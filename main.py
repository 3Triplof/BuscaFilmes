import os
import requests
from flask import Flask, request

app = Flask(__name__)

# CONFIGURAÇÕES
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# TMDb API
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"

# IDs de Gênero (TMDb)
GENRES = {
    "action": 28,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "fantasy": 14,
    "scifi": 878,
    "sci-fi": 878,
    "horror": 27,
    "mystery": 9648,
    "romance": 10749,
    "drama": 18
}

# --- FUNÇÃO DE INTERPRETAÇÃO (ATUALIZADA) ---
def interpretar_comando(texto):
    texto = texto.lower()
    busca = ""
    intencao = "normal"
    genre_id = None  # ID do gênero, se houver
    
    if "melhor" in texto or "top" in texto:
        intencao = "melhores"
    
    # Detecta categoria + gênero
    if "ficção" in texto or "sci-fi" in texto or "science fiction" in texto:
        busca = "sci-fi"
        genre_id = GENRES.get("scifi")
    elif "comédia" in texto or "comedy" in texto:
        busca = "comedy"
        genre_id = GENRES.get("comedy")
    elif "terror" in texto or "horror" in texto:
        busca = "horror"
        genre_id = GENRES.get("horror")
    elif "ação" in texto or "action" in texto:
        busca = "action"
        genre_id = GENRES.get("action")
    elif "romance" in texto or "romance" in texto:
        busca = "romance"
        genre_id = GENRES.get("romance")
    elif "animação" in texto or "animation" in texto:
        busca = "animation"
        genre_id = GENRES.get("animation")
    elif "mistério" in texto or "mystery" in texto:
        busca = "mystery"
        genre_id = GENRES.get("mystery")
    elif "fantasia" in texto or "fantasy" in texto:
        busca = "fantasy"
        genre_id = GENRES.get("fantasy")
    else:
        # Sem categoria: usa texto puro
        lixo = ["melhores", "filmes", "de", "os", "uma", "um", "top", "recomendar"]
        palavras = texto.split()
        busca = " ".join([p for p in palavras if p not in lixo])
        genre_id = None
    
    return busca, intencao, genre_id

# --- BUSCA LISTA DE FILMES (COM FILTRO POR GÊNERO) ---
def buscar_filme(termo, intencao, genre_id, chat_id, message_id):
    try:
        if genre_id:
            # Busca por GÊNERO (não por texto)
            params = {
                "api_key": TMDB_API_KEY,
                "with_genres": genre_id,
                "sort_by": "vote_average.desc" if intencao == "melhores" else "popularity.desc",
                "language": "pt-BR",
                "page": 1
            }
            response = requests.get(f"{TMDB_BASE}/discover/movie", params=params, timeout=10)
        else:
            # Busca por TEXTO (ex: "Matrix")
            params = {
                "api_key": TMDB_API_KEY,
                "query": termo,
                "language": "pt-BR"
            }
            response = requests.get(f"{TMDB_BASE}/search/movie", params=params, timeout=10)
        
        if response.status_code != 200:
            return "Erro na API TMDb (Status {}).".format(response.status_code)
        
        dados = response.json()
        
        if not dados.get("results"):
            return f"Nenhum filme encontrado para '{termo}'. Tente outro nome."
        
        lista_filmes = dados["results"]
        
        # Se intenção é "melhores" e não é filtro por gênero, ordena manualmente
        if intencao == "melhores" and not genre_id:
            lista_filmes.sort(key=lambda x: float(x.get('vote_average', 0)), reverse=True)
        
        top_filmes = lista_filmes[:10]
        
        texto = "🎥 *Top 10 Filmes Relacionados:*\n\n"
        texto += "Clique em um filme para mais informações:\n\n"
        
        buttons = []
        for i, filme in enumerate(top_filmes):
            titulo = filme.get('title', 'Unknown')
            poster_path = filme.get('poster_path', '')
            media_id = filme.get('id', '')
            
            nome_botao = f"{i+1}. {titulo}"
            dados_botao = f"movie:{media_id}"
            
            buttons.append([{"text": nome_botao, "callback_data": dados_botao}])
        
        payload = {
            "chat_id": chat_id,
            "text": texto,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": buttons
            }
        }
        
        requests.post(f"{BASE_URL}/sendMessage", json=payload)
        return "OK"
            
    except Exception as e:
        print(f"ERRO BUSCA: {type(e).__name__} - {str(e)}")
        return "Erro de conexão com TMDb."

# --- BUSCA DETALHES (POSTER + ELENCO + DIRETOR) ---
def buscar_detalhes(media_id, chat_id, callback_id):
    # 1. Detalhes do filme
    params_det = {
        "api_key": TMDB_API_KEY,
        "language": "pt-BR"
    }
    
    try:
        response_det = requests.get(f"{TMDB_BASE}/movie/{media_id}", params=params_det, timeout=10)
        
        if response_det.status_code != 200:
            return "Erro ao buscar detalhes."
        
        filme = response_det.json()
        
        # 2. Elenco + Crew (para pegar Diretor)
        params_cast = {
            "api_key": TMDB_API_KEY,
            "language": "pt-BR"
        }
        response_cast = requests.get(f"{TMDB_BASE}/movie/{media_id}/credits", params=params_cast, timeout=10)
        cast_data = response_cast.json() if response_cast.status_code == 200 else {}
        
        # Encontrar Diretor (crew)
        diretor = "Unknown"
        for member in cast_data.get('crew', []):
            if member.get('job') == 'Director':
                diretor = member.get('name', 'Unknown')
                break
        
        # Formata texto
        titulo = filme.get('title', 'Unknown')
        ano = filme.get('release_date', 'Unknown')[:4] if filme.get('release_date') else 'Unknown'
        generos = ", ".join([g.get('name', '') for g in filme.get('genres', [])])
        duracao = filme.get('runtime', 'Unknown')
        nota = filme.get('vote_average', 'Unknown')
        descricao = filme.get('overview', '')
        
        # Top 5 atores
        elenco = []
        for actor in cast_data.get('cast', [])[:5]:
            nome = actor.get('name', 'Unknown')
            personagem = actor.get('character', '')
            elenco.append(f"• {nome} ({personagem})")
        
        elenco_text = "\n".join(elenco)
        
        texto = f"""
🎬 *{titulo}*
📅 {ano}
⭐ Nota: {nota}/10
🎭 Gênero: {generos}
⏱️ Duração: {duracao} min
🎞️ Diretor: *{diretor}*

📝 *{descricao}*

🎞️ *Elenco Principal:*
{elenco_text}
"""
        
        # 3. Se tem poster, enviar imagem + texto
        poster_path = filme.get('poster_path', '')
        if poster_path:
            poster_url = f"{TMDB_IMG_BASE}{poster_path}"
            
            payload_img = {
                "chat_id": chat_id,
                "photo": poster_url,
                "caption": texto,
                "parse_mode": "Markdown"
            }
            requests.post(f"{BASE_URL}/sendPhoto", json=payload_img)
        else:
            payload_text = {
                "chat_id": chat_id,
                "text": texto,
                "parse_mode": "Markdown"
            }
            requests.post(f"{BASE_URL}/sendMessage", json=payload_text)
        
        return "OK"
            
    except Exception as e:
        print(f"ERRO DETALHES: {type(e).__name__} - {str(e)}")
        return "Erro ao buscar detalhes."

# --- WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json
    
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        message_id = update["message"]["message_id"]
        user_text = update["message"]["text"]
        
        termo_busca, intencao, genre_id = interpretar_comando(user_text)
        buscar_filme(termo_busca, intencao, genre_id, chat_id, message_id)
        
        return "OK"
    
    if "callback_query" in update:
        callback_id = update["callback_query"]["id"]
        chat_id = update["callback_query"]["message"]["chat"]["id"]
        dados_botao = update["callback_query"]["data"]
        
        if dados_botao.startswith("movie:"):
            media_id = dados_botao.split(":")[1]
            buscar_detalhes(media_id, chat_id, callback_id)
        
        return "OK"
    
    return "OK"

# --- SETUP ---
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
    else:
        return f"Erro: {response.text}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
