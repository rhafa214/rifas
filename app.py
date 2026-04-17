import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
import random
import time

# --- CONFIGURAÇÕES ---
ARQUIVO_DADOS = "rifa_dados_v2.json"
SENHA_MESTRE = "1234"

st.set_page_config(page_title="Rifa Master Pro", layout="wide", page_icon="🎟️")

# --- INICIALIZAÇÃO DO ESTADO (SESSION STATE) ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, "r") as f:
            return json.load(f)
    return {
        "config": {"total_numeros": 100, "preco": 10.0, "data_sorteio": "2024-12-31T20:00:00"},
        "vendas": {}
    }

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w") as f:
        json.dump(dados, f, indent=4)

# Carrega os dados para o uso no script
if 'dados' not in st.session_state:
    st.session_state.dados = carregar_dados()

dados = st.session_state.dados

# --- BARRA LATERAL (SISTEMA DE LOGIN) ---
st.sidebar.title("🔐 Painel Administrativo")

if not st.session_state.autenticado:
    # TELA DE LOGIN
    senha_input = st.sidebar.text_input("Digite a senha para acessar:", type="password")
    if st.sidebar.button("Acessar Painel"):
        if senha_input == SENHA_MESTRE:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.sidebar.error("Senha incorreta!")
else:
    # TELA LOGADA (A senha sumiu, aparece o botão de Sair)
    if st.sidebar.button("🚪 Sair do Painel (Bloquear)"):
        st.session_state.autenticado = False
        st.rerun()
    
    st.sidebar.divider()
    
    # FERRAMENTAS DO ADMINISTRADOR
    aba_admin = st.sidebar.tabs(["📝 Vender", "⚙️ Ajustes", "🗑️ Gerenciar"])
    
    with aba_admin[0]: # VENDER
        numeros_livres = [n for n in range(1, dados["config"]["total_numeros"] + 1) if str(n) not in dados["vendas"]]
        with st.form("venda_form", clear_on_submit=True):
            selecionados = st.multiselect("Números", options=numeros_livres)
            nome = st.text_input("Nome")
            tel = st.text_input("WhatsApp")
            pago = st.checkbox("Já está pago?")
            if st.form_submit_button("Confirmar"):
                if selecionados and nome:
                    for n in selecionados:
                        dados["vendas"][str(n)] = {"nome": nome, "tel": tel, "pago": pago, "data": datetime.now().strftime("%d/%m/%Y")}
                    salvar_dados(dados)
                    st.rerun()

    with aba_admin[1]: # AJUSTES
        novo_total = st.number_input("Total de Números", value=dados["config"]["total_numeros"])
        novo_preco = st.number_input("Preço (R$)", value=float(dados["config"]["preco"]))
        if st.button("Salvar Ajustes"):
            dados["config"]["total_numeros"] = novo_total
            dados["config"]["preco"] = novo_preco
            salvar_dados(dados)
            st.success("Configurações Salvas!")
        
        st.divider()
        # RESET COM DESMARCAÇÃO AUTOMÁTICA
        reset_check = st.checkbox("Habilitar Reset", key="chk_reset")
        if st.button("🔴 ZERAR TUDO", disabled=not reset_check):
            dados["vendas"] = {}
            salvar_dados(dados)
            st.session_state.chk_reset = False # Desmarca a caixa via código
            st.rerun()

    with aba_admin[2]: # GERENCIAR
        if dados["vendas"]:
            num_edit = st.selectbox("Editar Nº", options=sorted(dados["vendas"].keys(), key=int))
            info = dados["vendas"][num_edit]
            n_nome = st.text_input("Nome", value=info['nome'])
            n_pago = st.checkbox("Pago", value=info['pago'])
            col1, col2 = st.columns(2)
            if col1.button("Salvar"):
                dados["vendas"][num_edit].update({"nome": n_nome, "pago": n_pago})
                salvar_dados(dados)
                st.rerun()
            if col2.button("Excluir"):
                del dados["vendas"][num_edit]
                salvar_dados(dados)
                st.rerun()

# --- PAINEL PRINCIPAL (O QUE OS CLIENTES VEEM) ---
st.title("🎟️ Sistema de Gerenciamento de Rifa")

# Métricas
vendas = dados["vendas"]
pagos = sum(1 for v in vendas.values() if v["pago"])
arrecadado = pagos * dados["config"]["preco"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendidos", f"{len(vendas)} / {dados['config']['total_numeros']}")
c2.metric("Pagos (Verde)", pagos)
c3.metric("Arrecadado", f"R$ {arrecadado:.2f}")
c4.metric("Pendentes", f"R$ {(len(vendas)-pagos)*dados['config']['preco']:.2f}")

st.divider()

# SORTEADOR
st.subheader("🎲 Sorteio")
if st.button("🚀 INICIAR SORTEIO", use_container_width=True):
    placeholder = st.empty()
    apenas_pagos = [n for n, v in vendas.items() if v["pago"]]
    if apenas_pagos:
        for i in range(3, 0, -1):
            placeholder.markdown(f"<h1 style='text-align:center;'>{i}</h1>", unsafe_allow_html=True)
            time.sleep(1)
        vencedor = random.choice(apenas_pagos)
        st.balloons()
        placeholder.markdown(f"""
            <div style="text-align: center; background-color: #28a745; padding: 20px; border-radius: 15px; color: white;">
                <h1>🏆 GANHADOR: {int(vencedor):02d}</h1>
                <h3>👤 {vendas[vencedor]['nome']}</h3>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.error("Não há números pagos.")

st.divider()

# MAPA DE NÚMEROS (POPOVERS)
st.subheader("📍 Mapa de Números")
st.write("🟡 Disponível | 🔴 Pendente | 🟢 Pago")

col_grade = st.columns(10)
for i in range(1, dados["config"]["total_numeros"] + 1):
    n_str = str(i)
    with col_grade[(i-1) % 10]:
        if n_str in vendas:
            info = vendas[n_str]
            icon = "🟢" if info['pago'] else "🔴"
            with st.popover(f"{i:02d} {icon}", use_container_width=True):
                st.write(f"**Comprador:** {info['nome']}")
                st.write(f"**WhatsApp:** {info['tel']}")
                st.write(f"**Status:** {'Pago' if info['pago'] else 'Pendente'}")
        else:
            with st.popover(f"{i:02d} 🟡", use_container_width=True):
                st.write("✨ **Disponível!**")