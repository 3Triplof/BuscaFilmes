import os
import requests
from flask import Flask, request

app = Flask(__name__)

# CONFIGURAÇÕES GERAIS
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
TMDB_KEY = os.getenv("TMDB_API_KEY")  # pegue em https://www.themoviedb.org
BASE_TMDB = "https://api.themoviedb.org/3"

# Mapeamento de categorias (gêneros)
GENERO_MAP = {
    "animacao": {"tmdb_id": 16, "query": "animation"},
    "animação": {"tmdb_id": 16, "query": "animation"},
    "ação": {"tmdb_id": 28, "query": "action"},
    "acao": {"tmdb_id": 28, "query": "action"},
    "terror": {"tmdb_id": 27, "query": "horror"},
    "sci-fi": {"tmdb_id": 878, "query": "sci-fi"},
    "ficção": {"tmdb_id": 878, "query": "sci-fi"},
    "comedia": {"tmdb_id": 35, "query": "comedy"},
    "comédia": {"tmdb_id": 35, "query": "comedy"},
    "romance": {"tmdb_id": 10749, "query": "romance"},
}

def interpretar_comando(texto):
    texto = texto.lower()
    intencao = "normal"
    if "melhor" in texto or "top" in texto:
        intencao = "melhores"

    genero_id = None
    query = None

    # Detectar gênero
    for k, v in GENERO_MAP.items():
        if k in texto:
            genero_id = v["tmdb_id"]
            query = v["query"]
            break

    # Se não tem gênero, usar texto livre
    if not genero_id:
        lixo = ["melhores", "filmes", "de", "os", "uma", "um", "top", "recomendar"]
        palavras = texto.split()
        query = " ".join([p for p in palavras if p not in lixo]).strip()
        if not query:
            query = "movie"

    return query, intencao, genero_id

def buscar_filmes_tmdb(termo, intencao, genero_id):
    # Busca básica
    url = f"{BASE_TMDB}/search/movie"
    params = {
        "api_key": TMDB_KEY,
        "query": termo,
        "language": "pt-BR",
        "page": 1
    }
    if genero_id:
        params["with_genres"] = genero_id

    resp = requests.get(url, params=params, timeout=6)
    if resp.status_code != 200:
        return f"Erro na API TMDb (status {resp.status_code})."

    data = resp.json()
    results = data.get("results", [])
    if not results:
        return "Nenhum filme encontrado."

    # Se intenção for "melhores", ordenar por vote_average
    if intencao == "melhores":
        results.sort(key=lambda x: x.get("vote_average", 0), reverse=True)

    top = results[:10]
    msg = "🎥 *Top 10 Filmes Relacionados:*\n\n"

    for i, f in enumerate(top):
        titulo = f.get("title") or "Sem título"
        ano = (f.get("release_date") or "")[:4]
        nota = f.get("vote_average", 0)
        classificacao = obter_classificacao(f.get("id"))

        msg += f"{i+1}° *{titulo}* ({ano})\n"
        msg += f"   ⭐ {nota:.1f}/10 | 🇧🇷 Classificação: {classificacao}\n\n"

    return msg

def obter_classificacao(movie_id):
    # Endpoint de release dates para obter certification por país
    url = f"{BASE_TMDB}/movie/{movie_id}/release_dates"
    params = {"api_key": TMDB_KEY}
    try:
        r = requests.get(url, params=params, timeout=3)
        if r.status_code == 200:
            data = r.json()
            for res in data.get("results", []):
                if res.get("iso_3166_1") == "BR":
                    for rd in res.get("release_dates", []):
                        cert = rd.get("certification")
                        if cert:
                            return cert
    except:
        pass
    return "Não informado"

# --- WEBHOOK TELEGRAM ---
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        user_text = update["message"]["text"]

        termo, intencao, genero_id = interpretar_comando(user_text)
        resposta = buscar_filmes_tmdb(termo, intencao, genero_id)

        payload = {
            "chat_id": chat_id,
            "text": resposta,
            "parse_mode": "Markdown"
        }
        requests.post(f"{BASE_URL}/sendMessage", json=payload)

    return "OK"

@app.route("/setup", methods=["GET"])
def setup_webhook():
    my_url = os.getenv("RENDER_EXTERNAL_URL") + "/webhook"
    payload = {
        "url": my_url,
        "drop_pending_updates": True
    }
    response = requests.post(f"{BASE_URL}/setWebhook", json=payload)
    if response.status_code == 200:
        return f"Webhook configurado! URL: {my_url}"
    return f"Erro: {response.text}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
