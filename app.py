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

# --- CONFIGURAÇÕES DE ACESSO ---
SENHA_MESTRE = "1234" 
NOME_PLANILHA = "DB_Rifa"

st.set_page_config(page_title="Rifa Master Pro", layout="wide", page_icon="🏆")

# --- ESTILO CSS (VISUAL PROFISSIONAL) ---
st.markdown(
    """
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #ddd; }
        .main-title { text-align: center; color: #1E1E1E; font-family: 'Arial Black'; margin-bottom: 0px; }
        .countdown-box { text-align: center; background: #262730; color: #ffc107; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-weight: bold; }
        
        .btn-whatsapp { display: inline-flex; align-items: center; justify-content: center; background-color: #25D366; color: white !important; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; width: 100%; gap: 10px; transition: 0.3s; margin-top: 10px; }
        .btn-whatsapp:hover { background-color: #128C7E; transform: scale(1.02); text-decoration: none; }
        
        .btn-share { display: inline-flex; align-items: center; justify-content: center; background-color: #007bff; color: white !important; padding: 15px; border-radius: 8px; text-decoration: none; font-weight: bold; width: 100%; gap: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)
# No st.markdown do início do arquivo, adicione:
st.markdown("""
    <style>
    .winner-box {
        text-align: center;
        background: linear-gradient(135deg, #1e1e1e 0%, #343a40 100%);
        padding: 40px;
        border-radius: 20px;
        border: 5px solid #FFD700;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        margin: 20px auto;
        animation: pulse 2s infinite;
    }
    .winner-number {
        font-size: 120px !important;
        font-weight: 900;
        color: #FFD700;
        text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
        margin-bottom: 0px;
        line-height: 1;
    }
    .winner-name {
        font-size: 45px !important;
        color: white;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 10px;
    }
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 20px rgba(255, 215, 0, 0.2); }
        50% { transform: scale(1.02); box-shadow: 0 0 40px rgba(255, 215, 0, 0.5); }
        100% { transform: scale(1); box-shadow: 0 0 20px rgba(255, 215, 0, 0.2); }
    }
    </style>
    
    <!-- Script de Confetes Profissionais -->
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
    <script>
    function festa() {
        var duration = 5 * 1000;
        var animationEnd = Date.now() + duration;
        var defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 0 };

        function randomInRange(min, max) {
          return Math.random() * (max - min) + min;
        }

        var interval = setInterval(function() {
          var timeLeft = animationEnd - Date.now();

          if (timeLeft <= 0) {
            return clearInterval(interval);
          }

          var particleCount = 50 * (timeLeft / duration);
          confetti(Object.assign({}, defaults, { particleCount, origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 } }));
          confetti(Object.assign({}, defaults, { particleCount, origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 } }));
        }, 250);
    }
    </script>
""", unsafe_allow_html=True)
# --- CONEXÃO GOOGLE SHEETS ---
def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    except:
        creds = ServiceAccountCredentials.from_json_keyfile_dict("suas-credenciais.json", scope)
    client = gspread.authorize(creds)
    return client.open(NOME_PLANILHA)

def gerar_card_ganhador(numero, nome, premio, titulo_rifa, colocacao):
    # Configurações de Alta Definição
    largura = 1000
    altura = 1000
    img = Image.new('RGB', (largura, altura), color="#1E1E1E") # Fundo Escuro Elegante
    draw = ImageDraw.Draw(img)

    def carregar_fonte(tamanho):
        fontes = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf", 
            "arial.ttf"
        ]
        for f in fontes:
            try: return ImageFont.truetype(f, tamanho)
            except: continue
        return ImageFont.load_default()

    # Fontes
    f_titulo = carregar_fonte(45)
    f_parabens = carregar_fonte(80)
    f_numero = carregar_fonte(200)
    f_nome = carregar_fonte(70)
    f_premio = carregar_fonte(50)
    f_rodape = carregar_fonte(30)

    # Decoração (Círculos e Detalhes Dourados)
    draw.ellipse([-100, -100, 300, 300], outline="#FFD700", width=5)
    draw.ellipse([800, 800, 1100, 1100], outline="#FFD700", width=5)
    
    # Título da Rifa
    draw.text((largura//2, 80), titulo_rifa.upper(), fill="#FFD700", font=f_titulo, anchor="mm")
    
    # Texto "PARABÉNS"
    draw.text((largura//2, 200), "PARABÉNS!", fill="#FFFFFF", font=f_parabens, anchor="mm")
    
    # Círculo Central do Número
    cor_podio = "#FFD700" if str(colocacao) == "1" else "#C0C0C0" if str(colocacao) == "2" else "#CD7F32"
    draw.ellipse([350, 280, 650, 580], outline=cor_podio, width=15)
    
    # O Número Sorteado
    draw.text((largura//2, 430), str(numero), fill="#FFFFFF", font=f_numero, anchor="mm")
    
    # Nome do Ganhador
    draw.text((largura//2, 680), nome.upper(), fill=cor_podio, font=f_nome, anchor="mm")
    
    # O Prêmio
    draw.rectangle([150, 750, 850, 830], fill=cor_podio)
    draw.text((largura//2, 790), f"GANHOU: {premio}", fill="#1E1E1E", font=f_premio, anchor="mm")
    
    # Rodapé
    data_str = datetime.now().strftime("%d/%m/%Y")
    draw.text((largura//2, 920), f"Sorteio realizado em {data_str}", fill="#888888", font=f_rodape, anchor="mm")

    # Converter para Bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def carregar_dados():
    try:
        sh = conectar()
        # 1. Carrega Vendas (Robusto)
        ws_v = sh.worksheet("vendas")
        data_v = ws_v.get_all_values()
        vendas_dict = {}
        if len(data_v) > 1:
            df = pd.DataFrame(data_v[1:], columns=[c.strip().lower() for c in data_v[0]])
            for _, row in df.iterrows():
                num = str(row['numero']).strip()
                if num:
                    vendas_dict[num] = {
                        "nome": row.get('nome', 'Sem Nome'),
                        "tel": str(row.get('tel', '')),
                        "pago": str(row.get('pago', '')).upper() == 'TRUE',
                        "data": row.get('data', '')
                    }
        # 2. Carrega Config
        ws_c = sh.worksheet("config")
        conf_list = ws_c.get_all_records()
        if conf_list:
            conf = conf_list[0]
            # Fallbacks para colunas novas
            for k in ["titulo", "premio1", "premio2", "premio3", "data_sorteio"]:
                if k not in conf: conf[k] = ""
        else:
            conf = {"total_numeros": 100, "preco": 10.0, "titulo": "Rifa Master", "data_sorteio": "2024-12-31 20:00:00"}
        return {"config": conf, "vendas": vendas_dict}
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

# --- FUNÇÕES DE EDIÇÃO ---
def atualizar_venda_sheet(numero, nome, tel, pago):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel:
        ws.update_cell(cel.row, 2, nome)
        ws.update_cell(cel.row, 3, tel)
        ws.update_cell(cel.row, 4, str(pago).upper())

def excluir_venda_sheet(numero):
    sh = conectar(); ws = sh.worksheet("vendas")
    cel = ws.find(str(numero))
    if cel: ws.delete_rows(cel.row)

def salvar_config_sheet(titulo, total, preco, p1, p2, p3, data):
    sh = conectar(); ws = sh.worksheet("config")
    ws.update_cell(2, 1, int(total)); ws.update_cell(2, 2, float(preco))
    ws.update_cell(2, 3, str(titulo)); ws.update_cell(2, 4, str(p1))
    ws.update_cell(2, 5, str(p2)); ws.update_cell(2, 6, str(p3))
    ws.update_cell(2, 7, str(data))

# --- INICIALIZAÇÃO DE ESTADO ---
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'vencedores' not in st.session_state: st.session_state.vencedores = {}

dados = carregar_dados()
if not dados: st.stop()

# --- BARRA LATERAL (PAINEL ADMIN) ---
st.sidebar.title("🔐 Painel Administrativo")
if not st.session_state.autenticado:
    senha_in = st.sidebar.text_input("Senha Admin:", type="password")
    if st.sidebar.button("Entrar"):
        if senha_in == SENHA_MESTRE:
            st.session_state.autenticado = True
            st.rerun()
        else: st.sidebar.error("Senha Incorreta")
else:
    if st.sidebar.button("🚪 Sair do Painel"):
        st.session_state.autenticado = False
        st.rerun()
    
    st.sidebar.divider()
    abas_admin = st.sidebar.tabs(["📝 Venda", "✏️ Editar", "⚙️ Config"])
    
    with abas_admin[0]: # VENDER
        livres = [n for n in range(1, int(dados["config"]["total_numeros"])+1) if str(n) not in dados["vendas"]]
        with st.form("venda_rapida", clear_on_submit=True):
            nums_sel = st.multiselect("Números", livres)
            nome_sel = st.text_input("Nome")
            tel_sel = st.text_input("WhatsApp (Ex: 11999998888)")
            pago_sel = st.checkbox("Marcas como Pago?")
            if st.form_submit_button("Registrar Venda"):
                if nums_sel and nome_sel:
                    sh = conectar(); ws = sh.worksheet("vendas")
                    for n in nums_sel:
                        ws.append_row([str(n), nome_sel, tel_sel, str(pago_sel).upper(), datetime.now().strftime("%d/%m/%Y")])
                    st.rerun()

    with abas_admin[1]: # EDITAR / EXCLUIR
        if dados["vendas"]:
            n_ed = st.selectbox("Escolha o Número:", sorted(dados["vendas"].keys(), key=int))
            info = dados["vendas"][n_ed]
            new_nome = st.text_input("Nome", value=info['nome'])
            new_tel = st.text_input("Tel", value=info['tel'])
            new_pago = st.checkbox("Pago?", value=info['pago'])
            c1, c2 = st.columns(2)
            if c1.button("✅ Atualizar"):
                atualizar_venda_sheet(n_ed, new_nome, new_tel, new_pago); st.rerun()
            if c2.button("🗑️ Excluir"):
                excluir_venda_sheet(n_ed); st.rerun()

    with abas_admin[2]: # CONFIGS
        t_rifa = st.text_input("Título da Rifa", value=dados["config"]["titulo"])
        t_nums = st.number_input("Total Números", value=int(dados["config"]["total_numeros"]))
        t_prec = st.number_input("Preço R$", value=float(dados["config"]["preco"]))
        t_data = st.text_input("Data Sorteio (AAAA-MM-DD HH:MM:SS)", value=dados["config"]["data_sorteio"])
        p1 = st.text_input("1º Prêmio", value=dados["config"]["premio1"])
        p2 = st.text_input("2º Prêmio", value=dados["config"]["premio2"])
        p3 = st.text_input("3º Prêmio", value=dados["config"]["premio3"])
        if st.button("Salvar Configurações"):
            salvar_config_sheet(t_rifa, t_nums, t_prec, p1, p2, p3, t_data); st.rerun()
        if st.checkbox("Liberar Reset"):
            if st.button("🔴 ZERAR TUDO"):
                sh = conectar(); ws = sh.worksheet("vendas"); ws.clear()
                ws.append_row(["numero", "nome", "tel", "pago", "data"]); st.rerun()


# ---- Gerador de imagem -----#
def gerar_imagem_rifa(dados_vendas, total_n, titulo):
    # --- CONFIGURAÇÃO DE DIMENSÕES (Focado em proporção para celular) ---
    escala = 2
    largura = 1200
    margem = 50
    colunas_grid = 10
    tamanho_quadrado = 90
    espacamento_grid = 15
    
    # Cálculo do Grid
    linhas_grid = (total_n // colunas_grid) + (1 if total_n % colunas_grid != 0 else 0)
    altura_grid = linhas_grid * (tamanho_quadrado + espacamento_grid)
    
    # Cálculo da Lista de Nomes (3 COLUNAS para não ficar muito comprido)
    lista_nomes = sorted(dados_vendas.items(), key=lambda x: int(x[0]))
    itens_por_coluna = (len(lista_nomes) // 3) + (1 if len(lista_nomes) % 3 != 0 else 0)
    altura_lista = (max(itens_por_coluna, 1) * 40) + 100
    
    altura_header = 180
    altura_total = altura_header + altura_grid + altura_lista + 100
    
    # Criar Canvas
    img = Image.new('RGB', (largura, altura_total), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # --- SISTEMA DE FONTES ---
    def carregar_fonte(tamanho):
        fontes_caminhos = [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf", 
            "arial.ttf"
        ]
        for caminho in fontes_caminhos:
            try: return ImageFont.truetype(caminho, tamanho)
            except: continue
        return ImageFont.load_default()

    f_titulo = carregar_fonte(60)
    f_subtitulo = carregar_fonte(30)
    f_numero = carregar_fonte(45) # Números bem grandes
    f_legenda = carregar_fonte(28)
    f_lista = carregar_fonte(24)

    # --- CABEÇALHO (DARK) ---
    draw.rectangle([0, 0, largura, altura_header], fill="#1E1E1E")
    draw.text((largura//2, 70), titulo.upper(), fill="#FFC107", font=f_titulo, anchor="mm")
    draw.text((largura//2, 130), f"STATUS ATUALIZADO: {datetime.now().strftime('%d/%m %H:%M')}", fill="white", font=f_subtitulo, anchor="mm")

    # --- GRID DE NÚMEROS (CENTRALIZADO) ---
    largura_util_grid = (colunas_grid * (tamanho_quadrado + espacamento_grid)) - espacamento_grid
    x_offset = (largura - largura_util_grid) // 2
    y_offset = altura_header + 50

    for i in range(total_n):
        num = i + 1
        col = i % colunas_grid
        lin = i // colunas_grid
        x = x_offset + col * (tamanho_quadrado + espacamento_grid)
        y = y_offset + lin * (tamanho_quadrado + espacamento_grid)
        
        n_str = str(num)
        cor_fundo = "#E0E0E0" # Cinza claro para disponível
        cor_texto = "#333333"
        
        if n_str in dados_vendas:
            if dados_vendas[n_str].get('pago'):
                cor_fundo = "#2ECC71" # Verde forte
                cor_texto = "#FFFFFF"
            else:
                cor_fundo = "#E74C3C" # Vermelho forte
                cor_texto = "#FFFFFF"
        
        # Quadrado com borda
        draw.rectangle([x, y, x + tamanho_quadrado, y + tamanho_quadrado], fill=cor_fundo)
        # Número
        draw.text((x + tamanho_quadrado//2, y + tamanho_quadrado//2), f"{num:02d}", fill=cor_texto, font=f_numero, anchor="mm")

    # --- LEGENDA ---
    y_legenda = y_offset + altura_grid + 30
    leg_dados = [("#2ECC71", "PAGO"), ("#E74C3C", "RESERVADO"), ("#E0E0E0", "LIVRE")]
    x_leg = x_offset
    for cor, txt in leg_dados:
        draw.rectangle([x_leg, y_legenda, x_leg+30, y_legenda+30], fill=cor, outline="#333")
        draw.text((x_leg+40, y_legenda+15), txt, fill="#333", font=f_legenda, anchor="lm")
        x_leg += 250

    # --- LISTA DE NOMES EM 3 COLUNAS ---
    y_lista = y_legenda + 80
    draw.text((x_offset, y_lista), "PARTICIPANTES:", fill="#1E1E1E", font=f_legenda)
    y_item_base = y_lista + 50
    
    largura_coluna = (largura - (2 * margem)) // 3
    
    for idx, (n_venda, v) in enumerate(lista_nomes):
        col_atual = idx // itens_por_coluna
        lin_atual = idx % itens_por_coluna
        
        x_item = margem + (col_atual * largura_coluna)
        y_item = y_item_base + (lin_atual * 38)
        
        status_cor = "#2ECC71" if v.get('pago') else "#E74C3C"
        # Marcador colorido ao lado do nome
        draw.ellipse([x_item, y_item+10, x_item+15, y_item+25], fill=status_cor)
        # Texto: Num - Nome
        txt_venda = f"{int(n_venda):02d}: {v['nome'][:18]}"
        draw.text((x_item + 25, y_item + 18), txt_venda, fill="#333", font=f_lista, anchor="lm")

    # Gerar bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
# --- INTERFACE PRINCIPAL ---
st.markdown(f"<h1 class='main-title'>🎟️ {dados['config']['titulo']}</h1>", unsafe_allow_html=True)

# Cronômetro
try:
    alvo = datetime.strptime(dados["config"]["data_sorteio"], "%Y-%m-%d %H:%M:%S")
    dif = alvo - datetime.now()
    if dif.total_seconds() > 0:
        st.markdown(f"<div class='countdown-box'>⏳ Faltam {dif.days} dias, {dif.seconds//3600}h e {(dif.seconds//60)%60}m para o sorteio!</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='countdown-box' style='background:red; color:white;'>🏁 VENDAS ENCERRADAS!</div>", unsafe_allow_html=True)
except: pass

# Dashboard
vendas = dados["vendas"]
total_n = int(dados["config"]["total_numeros"])
v_count = len(vendas)
p_count = sum(1 for v in vendas.values() if v["pago"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendidos", f"{v_count} ({(v_count/total_n)*100:.1f}%)")
c2.metric("Disponíveis", total_n - v_count)
c3.metric("Confirmado", f"R$ {p_count * float(dados['config']['preco']):.2f}")
c4.metric("A Receber", f"R$ {(v_count - p_count) * float(dados['config']['preco']):.2f}")

st.divider()

# Abas Principais
t_mapa, t_sorteio, t_share, t_stats, t_pendentes = st.tabs([
    "🗺️ Mapa", "🎲 Sorteador", "📢 Divulgação", "📊 Relatório", "⚠️ Pendentes"
])

with t_mapa:
    # --- ÁREA DE BUSCA ---
    st.markdown("### 🔍 Consultar Meus Números")
    busca = st.text_input("Digite seu nome ou parte dele para encontrar seus números:", placeholder="Ex: João Silva")
    
    # Lógica de Busca
    if busca:
        # Filtra números que contenham o termo de busca no nome ou telefone
        resultados = {n: v for n, v in vendas.items() if busca.lower() in v['nome'].lower() or busca in v['tel']}
        
        if resultados:
            st.success(f"✅ Encontramos **{len(resultados)}** número(s) para '{busca}':")
            # Exibe os números em "badges" bonitos
            cols_res = st.columns(min(len(resultados), 5))
            for i, (n_achado, v_info) in enumerate(resultados.items()):
                status_icon = "🟢 (Pago)" if v_info['pago'] else "🔴 (Pendente)"
                cols_res[i % 5].metric(f"Nº {n_achado}", v_info['nome'], status_icon)
        else:
            st.warning(f"❌ Nenhum número encontrado para '{busca}'.")
    
    st.divider()

    # --- MAPA VISUAL (GRID) ---
    st.write("🟢 Pago | 🔴 Pendente | 🟡 Disponível")
    
    num_cols = 10 # No PC fica melhor com 10
    # Se quiser 5 colunas no celular, teria que usar CSS ou detectar largura, 
    # mas 5 ou 10 é um padrão seguro.
    
    for i in range(0, total_n, num_cols):
        cols = st.columns(num_cols)
        for j in range(num_cols):
            n = i + j + 1
            if n <= total_n:
                ns = str(n)
                with cols[j]:
                    # Lógica de destaque da busca
                    estilo_destaque = ""
                    if busca and ns in resultados:
                        # Se o número faz parte da busca, ele ganha uma borda azul
                        estilo_destaque = "border: 3px solid #007bff; box-shadow: 0px 0px 10px #007bff;"

                    if ns in vendas:
                        v = vendas[ns]
                        cor = "🟢" if v['pago'] else "🔴"
                        # Popover para ver detalhes do dono
                        with st.popover(f"{n:02d} {cor}", use_container_width=True):
                            st.write(f"👤 **Dono:** {v['nome']}")
                            if v['pago']:
                                st.success("Status: Pago")
                            else:
                                st.error("Status: Pendente")
                            
                            if st.session_state.autenticado and v['tel']:
                                t_l = re.sub(r'\D', '', v['tel'])
                                msg = urllib.parse.quote(f"Olá {v['nome']}, confirmando seu número {n} na {dados['config']['titulo']}!")
                                st.markdown(f'<a href="https://wa.me/55{t_l}?text={msg}" target="_blank" class="btn-whatsapp"><i class="fab fa-whatsapp"></i> WhatsApp</a>', unsafe_allow_html=True)
                    else:
                        # Número Livre
                        st.button(f"{n:02d} 🟡", key=f"btn_livre_{n}", use_container_width=True, disabled=True)
def exibir_vencedor_grande(n, nome, premio):
    # Função para disparar confetes via JS e mostrar o card
    st.markdown(f"""
        <div class="winner-box">
            <div style="color: #FFC107; font-size: 20px; font-weight: bold;">🏆 {premio.upper()} 🏆</div>
            <div class="winner-number">{n}</div>
            <div class="winner-name">{nome}</div>
        </div>
        <script>festa();</script>
    """, unsafe_allow_html=True)

with t_sorteio:
    st.subheader("🎲 Sorteio Oficial")
    
    # Botão de Reset
    if st.button("🗑️ Limpar Resultados"): 
        st.session_state.vencedores = {}
        st.rerun()

    pagos_l = [n for n, v in vendas.items() if v["pago"]]
    
    if not pagos_l:
        st.warning("Não há números pagos para sortear!")
    else:
        # Colunas para os botões de ação
        c1, c2, c3 = st.columns(3)
        
        # Lógica de Sorteio com Animação de "Giro"
        def realizar_sorteio(lista_disp, label_premio, key_venc):
            ph = st.empty()
            # Animação de sorteio rápido girando números
            for _ in range(20):
                n_aleatorio = random.choice(lista_disp)
                ph.markdown(f"<h1 style='text-align:center; font-size: 80px; color: gray;'>{n_aleatorio}</h1>", unsafe_allow_html=True)
                time.sleep(0.1)
            
            # Resultado Final
            venc_n = random.choice(lista_disp)
            st.session_state.vencedores[key_venc] = {"n": venc_n, "nome": vendas[venc_n]["nome"]}
            st.rerun()

        # Botões de Sorteio
        with c3:
            if st.button("Sortear 3º Prêmio 🥉", use_container_width=True):
                realizar_sorteio(pagos_l, "3º Prêmio", "3")
        with c2:
            if st.button("Sortear 2º Prêmio 🥈", use_container_width=True):
                lf = [n for n in pagos_l if n != st.session_state.vencedores.get("3",{}).get("n")]
                realizar_sorteio(lf, "2º Prêmio", "2")
        with c1:
            if st.button("Sortear 1º Prêmio 🥇", use_container_width=True):
                lf = [n for n in pagos_l if n not in [st.session_state.vencedores.get(x,{}).get("n") for x in ["2","3"]]]
                realizar_sorteio(lf, "1º Prêmio", "1")

        st.divider()

        # EXIBIÇÃO CENTRAL DO ÚLTIMO GANHADOR
        # Pegamos o sorteio mais recente para mostrar em destaque
        if st.session_state.vencedores:
            # Ordena para pegar o mais importante (1 > 2 > 3)
            ultimo_id = sorted(st.session_state.vencedores.keys())[0]
            venc = st.session_state.vencedores[ultimo_id]
            premio_nome = dados['config'].get(f'premio{ultimo_id}')
            
            # O SHOW DO GANHADOR
            exibir_vencedor_grande(venc['n'], venc['nome'], f"{ultimo_id}º Prêmio: {premio_nome}")
            
            # Botão para baixar o card que criamos anteriormente
            card_bytes = gerar_card_ganhador(venc['n'], venc['nome'], premio_nome, dados['config']['titulo'], ultimo_id)
            st.download_button(f"📥 Baixar Card de Vitória do {ultimo_id}º", card_bytes, f"ganhador_{ultimo_id}.png", "image/png")

        # Pequena tabela com todos os ganhadores abaixo
        if len(st.session_state.vencedores) > 1:
            st.write("### 📜 Outros Ganhadores")
            cols_v = st.columns(3)
            for i, k in enumerate(["1", "2", "3"]):
                if k in st.session_state.vencedores:
                    res = st.session_state.vencedores[k]
                    cols_v[i].info(f"**{k}º Lugar:** {res['n']} - {res['nome']}")
with t_share:
    st.subheader("📢 Gerar Card de Divulgação")
    
    # Cálculos para o texto
    v_count = len(vendas)
    p_count = sum(1 for v in vendas.values() if v.get('pago'))
    pendentes_pg = v_count - p_count
    restantes = total_n - v_count
    percentual = int((v_count / total_n) * 100)
    
    if st.button("🖼️ Gerar Imagem Ultra-HD"):
        with st.spinner("Criando imagem de alta resolução..."):
            img_bytes = gerar_imagem_rifa(vendas, total_n, dados['config']['titulo'])
            
            # Preview
            st.image(img_bytes, caption="Mapa da Rifa (Alta Resolução)", output_format="PNG", use_container_width=True)
            
            # Download
            st.download_button(
                label="📥 Baixar Imagem para Compartilhar",
                data=img_bytes,
                file_name=f"rifa_atualizada_{datetime.now().strftime('%d_%m_%H%M')}.png",
                mime="image/png"
            )

    st.divider()
    
    # --- CONSTRUÇÃO DO TEXTO PARA WHATSAPP ---
    prog = "🟢" * (percentual // 10) + "⚪" * (10 - (percentual // 10))
    
    txt = f"*📊 ATUALIZAÇÃO: {dados['config']['titulo']}*\n\n"
    txt += f"📈 *Progresso:* {prog} ({percentual}%)\n\n"
    
    txt += f"✅ *Total Vendidos:* {v_count}\n"
    txt += f"💰 *Pagos:* {p_count}\n"
    txt += f"⏳ *Faltam Pagar:* {pendentes_pg}\n"
    txt += f"🟡 *Ainda Disponíveis:* {restantes}\n\n"
    
    # Adiciona uma lista rápida de quem ainda não pagou (limitado a 10 para o texto não ficar gigante)
    lista_pendentes = [f"• Nº {n}: {v['nome']}" for n, v in vendas.items() if not v.get('pago')]
    if lista_pendentes:
        txt += "*⚠️ AGUARDANDO PAGAMENTO:* \n"
        txt += "\n".join(lista_pendentes[:10])
        if len(lista_pendentes) > 10:
            txt += f"\n_... e outros {len(lista_pendentes)-10} números_"
        txt += "\n\n"
    
    txt += "🔗 *Reserve o seu aqui:* https://sua-rifa.streamlit.app"
    # -----------------------------------------

    st.write("📝 **Legenda para copiar:**")
    st.text_area("Copie o texto abaixo:", value=txt, height=250)
    
    # Botão de compartilhar direto
    msg_u = urllib.parse.quote(txt)
    st.markdown(f'''
        <a href="https://wa.me/?text={msg_u}" target="_blank" class="btn-share">
            <i class="fab fa-whatsapp"></i> Compartilhar no Grupo
        </a>
    ''', unsafe_allow_html=True)
with t_pendentes:
    st.subheader("🟡 Controle de Recebimento")
    
    # Filtrar apenas quem NÃO pagou
    pendentes_dict = {n: v for n, v in vendas.items() if not v.get('pago')}
    
    if not pendentes_dict:
        st.success("🎉 Todos os números reservados já foram pagos!")
    else:
        col_list, col_msg = st.columns([1.6, 1])
        
        with col_list:
            st.write(f"Existem **{len(pendentes_dict)}** reservas aguardando pagamento.")
            
            # Estilo CSS para o botão amarelo (hack para mudar a cor do popover)
            st.markdown("""
                <style>
                div[data-testid="stPopover"] > button {
                    background-color: #FFD700 !important;
                    color: black !important;
                    border: 1px solid #B8860B !important;
                    font-weight: bold !important;
                    width: 100%;
                }
                div[data-testid="stPopover"] > button:hover {
                    background-color: #FFC107 !important;
                    border: 1px solid #000 !important;
                }
                </style>
            """, unsafe_allow_html=True)

            # Cabeçalho da Lista
            c1, c2, c3 = st.columns([0.8, 2, 1.5])
            c1.caption("Nº")
            c2.caption("NOME DO PARTICIPANTE")
            c3.caption("STATUS / AÇÃO")
            st.divider()

            # Lista de Pendentes
            for n_p in sorted(pendentes_dict.keys(), key=int):
                v_p = pendentes_dict[n_p]
                
                with st.container():
                    col_n, col_nome, col_acao = st.columns([0.8, 2, 1.5])
                    
                    col_n.markdown(f"### `{n_p:0>2}`")
                    col_nome.markdown(f"**{v_p['nome']}**\n\n{v_p['tel']}")
                    
                    # Botão estilo "Badge" Amarelo que abre confirmação
                    with col_acao.popover("🟡 PENDENTE", use_container_width=True):
                        st.write(f"Confirmar pagamento do número {n_p}?")
                        st.caption(f"Participante: {v_p['nome']}")
                        
                        if st.button("Confirmar ✅", key=f"conf_{n_p}", type="primary", use_container_width=True):
                            with st.spinner("Atualizando..."):
                                atualizar_venda_sheet(n_p, v_p['nome'], v_p['tel'], True)
                                st.toast(f"Número {n_p} confirmado!")
                                time.sleep(0.5)
                                st.rerun()
                    
                    st.divider()

        with col_msg:
            # --- PARTE DA MENSAGEM (IGUAL ANTERIOR, MAS MELHORADA) ---
            st.info("📢 **Cobrança Rápida**")
            
            txt_cobrar = f"*⚠️ LISTA DE PENDENTES - {dados['config']['titulo']}*\n"
            txt_cobrar += "------------------------------------------\n"
            txt_cobrar += "Olá! Segue a lista dos números que ainda não foram confirmados. "
            txt_cobrar += "Favor enviar o comprovante para garantir sua vaga! ⏳\n\n"
            
            for n_p in sorted(pendentes_dict.keys(), key=int):
                txt_cobrar += f"🟡 Nº {n_p:0>2} - {pendentes_dict[n_p]['nome']}\n"
            
            txt_cobrar += f"\n*Total:* {len(pendentes_dict)} números aguardando.\n"
            txt_cobrar += "🔗 https://sua-rifa.streamlit.app"
            
            st.text_area("Texto para o Grupo:", value=txt_cobrar, height=350)
            
            msg_encoded = urllib.parse.quote(txt_cobrar)
            st.markdown(f'''
                <a href="https://wa.me/?text={msg_encoded}" target="_blank" 
                   style="background-color: #25D366; color: white; padding: 15px; border-radius: 10px; 
                   text-decoration: none; display: flex; align-items: center; justify-content: center; 
                   font-weight: bold; gap: 10px;">
                   <i class="fab fa-whatsapp"></i> Postar Cobrança no Grupo
                </a>
            ''', unsafe_allow_html=True)
