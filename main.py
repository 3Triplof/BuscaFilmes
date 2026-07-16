import os
import requests
from flask import Flask, request

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TMDB_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
BASE_TMDB = "https://api.themoviedb.org/3"

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

    for k, v in GENERO_MAP.items():
        if k in texto:
            genero_id = v["tmdb_id"]
            query = v["query"]
            break

    if not genero_id:
        lixo = ["melhores", "filmes", "de", "os", "uma", "um", "top", "recomendar"]
        palavras = texto.split()
        query = " ".join([p for p in palavras if p not in lixo]).strip()
        if not query:
            query = "movie"

    return query, intencao, genero_id

def buscar_filmes_tmdb(termo, intencao, genero_id):
    url = f"{BASE_TMDB}/search/movie"
    params = {
        "api_key": TMDB_KEY,
        "query": termo,
        "language": "pt-BR",
        "page": 1
    }
    resp = requests.get(url, params=params, timeout=6)
    if resp.status_code != 200:
        return [], "Erro na API TMDb."

    data = resp.json()
    results = data.get("results", [])

    if genero_id:
        results = [f for f in results if genero_id in f.get("genre_ids", [])]

    if not results:
        return [], "Nenhum filme encontrado."

    if intencao == "melhores":
        results.sort(key=lambda x: x.get("vote_average", 0), reverse=True)

    return results[:10], None

def obter_classificacao(movie_id):
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

def obter_detalhes(movie_id):
    movie_url = f"{BASE_TMDB}/movie/{movie_id}"
    credits_url = f"{BASE_TMDB}/movie/{movie_id}/credits"

    movie = requests.get(movie_url, params={"api_key": TMDB_KEY, "language": "pt-BR"}, timeout=6).json()
    credits = requests.get(credits_url, params={"api_key": TMDB_KEY, "language": "pt-BR"}, timeout=6).json()

    titulo = movie.get("title", "Sem título")
    ano = (movie.get("release_date") or "")[:4]
    sinopse = movie.get("overview") or "Sinopse não disponível."
    nota = movie.get("vote_average", 0)
    classificacao = obter_classificacao(movie_id)

    diretor = "Não informado"
    for crew in credits.get("crew", []):
        if crew.get("job") == "Director":
            diretor = crew.get("name", "Não informado")
            break

    elenco = [c.get("name") for c in credits.get("cast", [])[:5] if c.get("name")]
    elenco_txt = ", ".join(elenco) if elenco else "Não informado"

    poster = movie.get("poster_path")
    poster_url = f"https://image.tmdb.org/t/p/w500{poster}" if poster else None

    texto = (
        f"🎬 *{titulo}* ({ano})\n"
        f"⭐ Nota: {nota:.1f}/10\n"
        f"🇧🇷 Classificação: {classificacao}\n"
        f"🎥 Direção: {diretor}\n"
        f"👥 Elenco: {elenco_txt}\n\n"
        f"📝 {sinopse}"
    )
    return texto, poster_url

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json

    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        user_text = update["message"]["text"]

        termo, intencao, genero_id = interpretar_comando(user_text)
        filmes, erro = buscar_filmes_tmdb(termo, intencao, genero_id)

        if erro:
            requests.post(f"{BASE_URL}/sendMessage", json={"chat_id": chat_id, "text": erro})
            return "OK"

        keyboard = []
        msg = "🎥 *Escolha um filme:*\n\n"
        for f in filmes:
            titulo = f.get("title", "Sem título")
            ano = (f.get("release_date") or "")[:4]
            movie_id = f.get("id")
            keyboard.append([{
                "text": f"{titulo} ({ano})",
                "callback_data": f"movie:{movie_id}"
            }])

        payload = {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": keyboard}
        }
        requests.post(f"{BASE_URL}/sendMessage", json=payload)

    elif "callback_query" in update:
        cq = update["callback_query"]
        query_id = cq["id"]
        data = cq.get("data", "")
        chat_id = cq["message"]["chat"]["id"]
        message_id = cq["message"]["message_id"]

        requests.post(f"{BASE_URL}/answerCallbackQuery", json={"callback_query_id": query_id})

        if data.startswith("movie:"):
            movie_id = data.split(":", 1)[1]
            texto, poster_url = obter_detalhes(movie_id)

            requests.post(
                f"{BASE_URL}/editMessageText",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": texto,
                    "parse_mode": "Markdown"
                }
            )

            requests.post(
                f"{BASE_URL}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {}
                }
            )

            if poster_url:
                requests.post(
                    f"{BASE_URL}/sendPhoto",
                    json={
                        "chat_id": chat_id,
                        "photo": poster_url
                    }
                )

    return "OK"

@app.route("/setup", methods=["GET"])
def setup_webhook():
    my_url = os.getenv("RENDER_EXTERNAL_URL") + "/webhook"
    payload = {"url": my_url, "drop_pending_updates": True}
    response = requests.post(f"{BASE_URL}/setWebhook", json=payload)
    return response.text

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
