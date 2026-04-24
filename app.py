import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import random
import time
import urllib.parse
import re
from PIL import Image, ImageDraw, ImageFont
import io

# --- 1. CONFIGURAÇÕES BÁSICAS ---
SENHA_MESTRE = "1234" 
NOME_PLANILHA = "DB_Rifa"
st.set_page_config(page_title="Rifa Master Pro", layout="wide", page_icon="🏆")

# --- 2. ESTILOS E SCRIPTS CONSOLIDADOS ---
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #ddd; }
        .main-title { text-align: center; color: #1E1E1E; font-family: 'Arial Black'; margin-bottom: 0px; }
        .countdown-box { text-align: center; background: #262730; color: #ffc107; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-weight: bold; }
        .btn-whatsapp { display: inline-flex; align-items: center; justify-content: center; background-color: #25D366; color: white !important; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; width: 100%; gap: 10px; margin-top: 10px; }
        .btn-share { display: inline-flex; align-items: center; justify-content: center; background-color: #007bff; color: white !important; padding: 15px; border-radius: 8px; text-decoration: none; font-weight: bold; width: 100%; gap: 10px; }
        
        /* Overlay de Ganhador */
        .overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.85); backdrop-filter: blur(12px); z-index: 999999; display: flex; justify-content: center; align-items: center; flex-direction: column; }
        .winner-card-xl { background: #1a1a1a; padding: 50px; border-radius: 30px; border: 4px solid #FFD700; text-align: center; color: white; box-shadow: 0 0 80px rgba(255, 215, 0, 0.3); }
        
        /* Ajuste do Popover Amarelo */
        div[data-testid="stPopover"] > button { background-color: #FFD700 !important; color: black !important; font-weight: bold !important; width: 100%; }
    </style>

    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
    <script>
    function festa() {
        var end = Date.now() + (5 * 1000);
        (function frame() {
            confetti({ particleCount: 3, angle: 60, spread: 55, origin: { x: 0 }, colors: ['#FFD700', '#ffffff'] });
            confetti({ particleCount: 3, angle: 120, spread: 55, origin: { x: 1 }, colors: ['#FFD700', '#ffffff'] });
            if (Date.now() < end) { requestAnimationFrame(frame); }
        }());
    }
    function fecharAutomatico(segundos) {
        setTimeout(function() {
            const botoes = window.parent.document.querySelectorAll('button');
            for (let b of botoes) { if (b.innerText.includes('FECHAR E VOLTAR')) { b.click(); } }
        }, segundos * 1000);
    }
    </script>
""", unsafe_allow_html=True)

# --- 3. FUNÇÕES DE DADOS (GOOGLE SHEETS) ---
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_dict("suas-credenciais.json", scope)
    return gspread.authorize(creds).open(NOME_PLANILHA)

def carregar_dados():
    try:
        sh = conectar()
        ws_v = sh.worksheet("vendas")
        data_v = ws_v.get_all_values()
        vendas_dict = {}
        if len(data_v) > 1:
            df = pd.DataFrame(data_v[1:], columns=[c.strip().lower() for c in data_v[0]])
            for _, row in df.iterrows():
                num = str(row['numero']).strip()
                if num:
                    vendas_dict[num] = {"nome": row.get('nome', 'Sem Nome'), "tel": str(row.get('tel', '')), "pago": str(row.get('pago', '')).upper() == 'TRUE', "data": row.get('data', '')}
        
        ws_c = sh.worksheet("config")
        conf_list = ws_c.get_all_records()
        conf = conf_list[0] if conf_list else {"total_numeros": 100, "preco": 10.0, "titulo": "Rifa Master", "data_sorteio": "2024-12-31 20:00:00"}
        return {"config": conf, "vendas": vendas_dict}
    except Exception as e:
        st.error(f"Erro de Conexão: {e}"); return None

def atualizar_venda_sheet(numero, nome, tel, pago):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel:
        ws.update_cell(cel.row, 2, nome); ws.update_cell(cel.row, 3, tel); ws.update_cell(cel.row, 4, str(pago).upper())

def salvar_config_sheet(titulo, total, preco, p1, p2, p3, data):
    sh = conectar(); ws = sh.worksheet("config")
    ws.update_cell(2, 1, int(total)); ws.update_cell(2, 2, float(preco)); ws.update_cell(2, 3, str(titulo))
    ws.update_cell(2, 4, str(p1)); ws.update_cell(2, 5, str(p2)); ws.update_cell(2, 6, str(p3)); ws.update_cell(2, 7, str(data))

# --- 4. FUNÇÕES DE IMAGEM (HD) ---
def carregar_fonte(tamanho):
    fontes = ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:\\Windows\\Fonts\\arialbd.ttf", "arial.ttf"]
    for f in fontes:
        try: return ImageFont.truetype(f, tamanho)
        except: continue
    return ImageFont.load_default()

def gerar_card_ganhador(numero, nome, premio, titulo_rifa, colocacao):
    img = Image.new('RGB', (1000, 1000), color="#1E1E1E")
    draw = ImageDraw.Draw(img)
    f_p = carregar_fonte(80); f_n = carregar_fonte(200); f_nom = carregar_fonte(70); f_pre = carregar_fonte(50)
    
    cor_podio = "#FFD700" if str(colocacao) == "1" else "#C0C0C0" if str(colocacao) == "2" else "#CD7F32"
    draw.text((500, 200), "PARABÉNS!", fill="#FFFFFF", font=f_p, anchor="mm")
    draw.ellipse([350, 280, 650, 580], outline=cor_podio, width=15)
    draw.text((500, 430), str(numero), fill="#FFFFFF", font=f_n, anchor="mm")
    draw.text((500, 680), nome.upper(), fill=cor_podio, font=f_nom, anchor="mm")
    draw.rectangle([150, 750, 850, 830], fill=cor_podio)
    draw.text((500, 790), f"GANHOU: {premio}", fill="#1E1E1E", font=f_pre, anchor="mm")
    
    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

def gerar_imagem_rifa(dados_vendas, total_n, titulo):
    largura = 1200; colunas_grid = 10; tamanho_q = 90; espaco = 15; margem = 50
    linhas_grid = (total_n // colunas_grid) + (1 if total_n % colunas_grid != 0 else 0)
    lista_nomes = sorted(dados_vendas.items(), key=lambda x: int(x[0]))
    itens_col = (len(lista_nomes) // 3) + (1 if len(lista_nomes) % 3 != 0 else 0)
    altura_total = 180 + (linhas_grid * (tamanho_q + espaco)) + (max(itens_col, 1) * 40) + 200
    
    img = Image.new('RGB', (largura, altura_total), color="#FFFFFF"); draw = ImageDraw.Draw(img)
    f_t = carregar_fonte(60); f_n = carregar_fonte(45); f_l = carregar_fonte(24)
    
    draw.rectangle([0, 0, largura, 180], fill="#1E1E1E")
    draw.text((largura//2, 70), titulo.upper(), fill="#FFC107", font=f_t, anchor="mm")
    
    x_off = (largura - (colunas_grid * (tamanho_q + espaco) - espaco)) // 2
    for i in range(total_n):
        n_s = str(i+1)
        cor = "#2ECC71" if n_s in dados_vendas and dados_vendas[n_s]['pago'] else "#E74C3C" if n_s in dados_vendas else "#E0E0E0"
        x = x_off + (i % colunas_grid) * (tamanho_q + espaco)
        y = 230 + (i // colunas_grid) * (tamanho_q + espaco)
        draw.rectangle([x, y, x + tamanho_q, y + tamanho_q], fill=cor)
        draw.text((x + tamanho_q//2, y + tamanho_q//2), f"{i+1:02d}", fill="white" if cor != "#E0E0E0" else "#333", font=f_n, anchor="mm")
    
    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

# --- 5. INICIALIZAÇÃO E CARREGAMENTO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'vencedores' not in st.session_state: st.session_state.vencedores = {}
if 'mostrar_modal' not in st.session_state: st.session_state.mostrar_modal = False
if 'venc_temp' not in st.session_state: st.session_state.venc_temp = {}

dados = carregar_dados()
if not dados: st.stop()
vendas = dados["vendas"]
total_n = int(dados["config"]["total_numeros"])

# --- 6. BARRA LATERAL (ADMIN) ---
st.sidebar.title("🔐 Painel Admin")
if not st.session_state.autenticado:
    if st.sidebar.text_input("Senha:", type="password") == SENHA_MESTRE:
        st.session_state.autenticado = True; st.rerun()
else:
    if st.sidebar.button("Sair"): st.session_state.autenticado = False; st.rerun()
    aba_adm = st.sidebar.tabs(["📝 Venda", "⚙️ Config"])
    with aba_adm[0]:
        livres = [n for n in range(1, total_n+1) if str(n) not in vendas]
        with st.form("venda"):
            n_sel = st.multiselect("Números", livres)
            nome_s = st.text_input("Nome")
            tel_s = st.text_input("WhatsApp")
            pago_s = st.checkbox("Pago?")
            if st.form_submit_button("Vender"):
                sh = conectar(); ws = sh.worksheet("vendas")
                for n in n_sel: ws.append_row([str(n), nome_s, tel_s, str(pago_s).upper(), datetime.now().strftime("%d/%m/%Y")])
                st.rerun()
    with aba_adm[1]:
        if st.button("Salvar Configs"): salvar_config_sheet(t_rifa, t_nums, t_prec, p1, p2, p3, t_data); st.rerun()

# --- 7. INTERFACE PRINCIPAL ---
st.markdown(f"<h1 class='main-title'>🏆 {dados['config']['titulo']}</h1>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendidos", len(vendas))
c2.metric("Livres", total_n - len(vendas))
c3.metric("Confirmado", f"R$ {sum(1 for v in vendas.values() if v['pago']) * float(dados['config']['preco']):.2f}")
c4.metric("Restante", f"R$ {(len(vendas) - sum(1 for v in vendas.values() if v['pago'])) * float(dados['config']['preco']):.2f}")

t_mapa, t_sorteio, t_share, t_pendentes = st.tabs(["🗺️ Mapa", "🎲 Sorteio", "📢 Divulgar", "⚠️ Pendentes"])

with t_mapa:
    busca = st.text_input("🔍 Buscar por nome:")
    resultados = {n: v for n, v in vendas.items() if busca.lower() in v['nome'].lower()} if busca else {}
    if resultados: st.info(f"Números de {busca}: {', '.join(resultados.keys())}")
    
    cols = st.columns(10)
    for i in range(1, total_n + 1):
        n_s = str(i)
        with cols[(i-1)%10]:
            if n_s in vendas:
                v = vendas[n_s]
                cor = "🟢" if v['pago'] else "🔴"
                with st.popover(f"{i:02d} {cor}", use_container_width=True):
                    st.write(f"👤 {v['nome']}")
                    if st.session_state.autenticado and v['tel']:
                        st.markdown(f'<a href="https://wa.me/{re.sub(r"\D", "", v["tel"])}" class="btn-whatsapp">WhatsApp</a>', unsafe_allow_html=True)
            else: st.button(f"{i:02d} 🟡", disabled=True, use_container_width=True)

with t_sorteio:
    pagos_l = [n for n, v in vendas.items() if v["pago"]]
    c1, c2, c3 = st.columns(3)
    
    def girar_e_sortear(lista, premio, chave):
        ph = st.empty()
        for _ in range(15):
            ph.markdown(f"<h1 style='text-align:center; color:#FFD700;'>{random.choice(lista)}</h1>", unsafe_allow_html=True); time.sleep(0.1)
        escolhido = random.choice(lista)
        st.session_state.venc_temp = {"n": escolhido, "nome": vendas[escolhido]["nome"], "premio": premio, "chave": chave}
        st.session_state.vencedores[chave] = st.session_state.venc_temp
        st.session_state.mostrar_modal = True; ph.empty(); st.rerun()

    if c1.button("Sortear 1º 🥇"): girar_e_sortear(pagos_l, dados['config']['premio1'], "1")
    if c2.button("Sortear 2º 🥈"): girar_e_sortear(pagos_l, dados['config']['premio2'], "2")
    if c3.button("Sortear 3º 🥉"): girar_e_sortear(pagos_l, dados['config']['premio3'], "3")

    # MODAL DE GANHADOR
    if st.session_state.get('mostrar_modal'):
        v = st.session_state.venc_temp
        st.markdown(f"""<div class='overlay'><div class='winner-card-xl'><h2 style='color:#FFD700;'>🏆 {v['premio']}</h2><p style='font-size:150px; font-weight:900; margin:0;'>{v['n']}</p><p style='font-size:50px;'>{v['nome']}</p></div></div>
        <script>festa(); fecharAutomatico(15);</script>""", unsafe_allow_html=True)
        if st.button("❌ FECHAR E VOLTAR", type="primary", use_container_width=True):
            st.session_state.mostrar_modal = False; st.rerun()
        card = gerar_card_ganhador(v['n'], v['nome'], v['premio'], dados['config']['titulo'], v['chave'])
        st.download_button("📥 BAIXAR CARD", card, "ganhador.png", use_container_width=True)

    if st.session_state.vencedores and not st.session_state.mostrar_modal:
        st.divider(); st.subheader("📜 Ganhadores")
        for k, v in st.session_state.vencedores.items(): st.success(f"{k}º Lugar: {v['n']} - {v['nome']}")

with t_share:
    if st.button("🖼️ GERAR MAPA HD"):
        img = gerar_imagem_rifa(vendas, total_n, dados['config']['titulo'])
        st.image(img); st.download_button("📥 Baixar Mapa", img, "mapa.png")

with t_pendentes:
    pends = {n: v for n, v in vendas.items() if not v['pago']}
    for n, v in pends.items():
        c_n, c_nom, c_ac = st.columns([1,3,2])
        c_n.write(f"Nº {n}"); c_nom.write(v['nome'])
        with c_ac.popover("🟡 PENDENTE", use_container_width=True):
            if st.button("Confirmar ✅", key=f"p_{n}"):
                atualizar_venda_sheet(n, v['nome'], v['tel'], True); st.rerun()
