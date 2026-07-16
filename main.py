import os
import requests
from flask import Flask, request

app = Flask(__name__)

# CONFIGURAÇÕES
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
URL_FILMES = "https://imdb.iamidiotareyoutoo.com/search"

# --- FUNÇÃO DE INTERPRETAÇÃO (RETORNA BUSCA + INTENÇÃO) ---
def interpretar_comando(texto):
    texto = texto.lower()
    busca = ""
    intencao = "normal"  # Pode ser "normal" ou "melhores"
    
    # Detecta intenção
    if "melhor" in texto or "top" in texto:
        intencao = "melhores"
    
    # Detecta categoria
    if "ficção" in texto or "sci-fi" in texto or "science fiction" in texto:
        busca = "sci-fi"
    elif "comédia" in texto or "comedy" in texto:
        busca = "comedy"
    elif "terror" in texto or "horror" in texto:
        busca = "horror"
    elif "ação" in texto or "action" in texto:
        busca = "action"
    elif "romance" in texto or "romance" in texto:
        busca = "romance"
    else:
        # Sem categoria: usa texto puro
        lixo = ["melhores", "filmes", "de", "os", "uma", "um", "top", "recomendar"]
        palavras = texto.split()
        busca = " ".join([p for p in palavras if p not in lixo])
    
    return busca, intencao

# --- FUNÇÃO DE BUSCA (MOSTRA TOP 10 SEMPRE) ---
def buscar_filme(termo, intencao):
    params = {"q": termo}
    
    try:
        response = requests.get(URL_FILMES, params=params, timeout=5)
        
        if response.status_code != 200:
            return f"Erro na API (Status {response.status_code})."
        
        dados = response.json()
        
        if not dados.get("ok") or not dados.get("description"):
            return f"Nenhum filme encontrado para '{termo}'. Tente outro nome."
        
        lista_filmes = dados["description"]
        
        # Se intenção é "melhores", ordena por RANK
        if intencao == "melhores":
            lista_filmes.sort(key=lambda x: int(x.get('#RANK', 999999)))
        
        # MOSTRA TOP 10 SEMPRE
        top_filmes = lista_filmes[:10]
        
        resposta = "🎥 *Top 10 Filmes Relacionados:*\n\n"
        for i, filme in enumerate(top_filmes):
            titulo = filme.get('#TITLE', 'Unknown')
            ano = filme.get('#YEAR', 'Unknown')
            rank = filme.get('#RANK', 'Unknown')
            
            resposta += f"{i+1}° *{titulo}* ({ano})\n"
            resposta += f"   🏆 Rank: {rank}\n\n"
        
        return respuesta
            
    except Exception as e:
        print(f"ERRO DE CONEXÃO: {str(e)}")
        return "Erro de conexão com a API de filmes."

# --- ENDPOINT WEBHOOK ---
@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json
    
    if "message" in update and "text" in update["message"]:
        chat_id = update["message"]["chat"]["id"]
        user_text = update["message"]["text"]
        
        # 1. INTERPRETA (busca + intencao)
        termo_busca, intencao = interpretar_comando(user_text)
        
        # 2. Busca na API (passa intencao)
        resposta = buscar_filme(termo_busca, intencao)
        
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
