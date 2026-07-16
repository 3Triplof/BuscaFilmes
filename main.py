import os
import requests
from flask import Flask, request

app = Flask(__name__)

# CONFIGURAÇÕES
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
URL_FILMES = "https://imdb.iamidiotareyoutoo.com/search"

# --- FUNÇÃO DE INTERPRETAÇÃO (Novo!) ---
def interpretar_comando(texto):
    texto = texto.lower()
    busca = ""
    
    # Detecta categoria
    if "ficção" in texto or "sci-fi" in texto or "science fiction" in texto:
        busca = "sci-fi" # A API busca melhor em inglês
    elif "comédia" in texto or "comedy" in texto:
        busca = "comedy"
    elif "terror" in texto or "horror" in texto:
        busca = "horror"
    elif "ação" in texto or "action" in texto:
        busca = "action"
    elif "romance" in texto or "romance" in texto:
        busca = "romance"
    else:
        # Se não tem categoria, busca pelo texto puro (ex: "Matrix")
        # Remove palavras como "melhores", "filmes", etc.
        lixo = ["melhores", "filmes", "de", "os", "uma", "um", "top", "recomendar"]
        palavras = texto.split()
        busca = " ".join([p for p in palavras if p not in lixo])
    
    return busca

# --- FUNÇÃO DE BUSCA ---
def buscar_filme(termo):
    # Se o termo veio da interpretação (ex: "sci-fi"), usa ele.
    # Se veio da busca direta (ex: "Matrix"), o termo já é o nome.
    params = {"q": termo}
    response = requests.get(URL_FILMES, params=params)
    
    if response.status_code == 200:
        dados = response.json()
        if dados.get("results"):
            lista_filmes = dados["results"]
            
            # Se o usuário disse "melhores", ordena por nota (rating)
            if "melhor" in termo.lower() or "top" in termo.lower():
                lista_filmes.sort(key=lambda x: float(x.get('rating', 0)), reverse=True)
                melhores = lista_filmes[:3]
                
                resposta = "🎥 *Top 3 Filmes Relacionados:*\n\n"
                for i, filme in enumerate(melhores):
                    resposta += f"{i+1}° *{filme['title']}* ({filme['year']})\n"
                    resposta += f"   ⭐ {filme['rating']}/10\n"
                    resposta += f"   📝 {filme['description'][:80]}...\n\n"
                return resposta
            
            # Se não é "melhores", mostra apenas o primeiro resultado
            filme = lista_filmes[0]
            return f"🎬 *{filme['title']}*\n📅 {filme['year']}\n⭐ {filme['rating']}/10\n📝 {filme['description'][:150]}..."
            
    return "Filme não encontrado ou erro na API."

# --- ENDPOINT WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json
    
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        user_text = update["message"]["text"]
        
        # 1. INTERPRETA o que o usuário quer
        termo_busca = interpretar_comando(user_text)
        
        # 2. Busca na API
        resposta = buscar_filme(termo_busca)
        
        # 3. Responde
        payload = {
            "chat_id": chat_id,
            "text": resposta,
            "parse_mode": "Markdown"
        }
        requests.post(f"{BASE_URL}/sendMessage", json=payload)
    
    return "OK"

# --- CONFIGURAÇÃO DO WEBHOOK (Rodar apenas uma vez) ---
@app.route("/setup", methods=["GET"])
def setup_webhook():
    # URL do seu Render
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
