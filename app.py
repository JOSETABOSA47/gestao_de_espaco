import streamlit as st
import pandas as pd
from fpdf import FPDF
import json
import os
import hashlib

# --- CONFIGURAÇÃO DA PÁGINA (LINHA OBRIGATÓRIA NO INÍCIO) ---
st.set_page_config(
    page_title="Portal Logístico",
    page_icon="logo.png", # Ou "🚛" se ainda não subiu a logo
    layout="wide",
    initial_sidebar_state="expanded" # <--- ISSO FORÇA O MENU A APARECER ABERTO
)

# ==============================================================================
# 2. CSS VISUAL (CORRIGIDO PARA NÃO SUMIR COM A BARRA LATERAL)
# ==============================================================================
# Remove ícones e barra superior do Streamlit
hide_streamlit_style = """
<style>
/* Remove o menu do Streamlit (os três pontinhos) */
#MainMenu {visibility: hidden;}

/* Remove o botão de edição do código */
button[kind="header"], .st-emotion-cache-15ecox0 {display: none !important;}

/* Remove o rodapé "Made with Streamlit" */
footer {visibility: hidden;}

/* Remove o ícone do GitHub no header */
header div:nth-child(3) {display: none !important;}
</style>
"""

st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==============================================================================
# 1. Defina aqui seu usuário e senha MESTRES.
# Eles NÃO podem ser alterados pelo site, apenas editando este código.
USUARIO_MASTER = "admintabosa"
# Tenta pegar a senha dos Segredos do Streamlit (Nuvem)
# Se não encontrar (ex: rodando no seu PC sem configurar), usa uma senha padrão
try:
    SENHA_MASTER_FIXA = st.secrets["admin_password"]
except FileNotFoundError:
    # Senha provisória apenas para quando você testar no seu PC local
    SENHA_MASTER_FIXA = "123456"

# ==============================================================================

ARQUIVO_CREDENCIAIS = 'credenciais.json'
DADOS_PADRAO = {
    "VUC Padrão": {"categoria": "Veículo", "comp": 4.50, "larg": 2.20, "alt": 2.30, "peso_max": 3500},
}

# --- FUNÇÕES DE SEGURANÇA ---
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha_digitada, hash_salvo):
    return criptografar_senha(senha_digitada) == hash_salvo

# --- GERENCIAMENTO DE USUÁRIOS ---
def carregar_usuarios():
    if os.path.exists(ARQUIVO_CREDENCIAIS):
        try:
            with open(ARQUIVO_CREDENCIAIS, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_novo_usuario(usuario, senha):
    # TRAVA DE SEGURANÇA: Impede criar usuário com nome do patrão
    if usuario.lower() == USUARIO_MASTER:
        return False 
        
    usuarios = carregar_usuarios()
    if usuario in usuarios: return False
    
    usuarios[usuario] = criptografar_senha(senha)
    with open(ARQUIVO_CREDENCIAIS, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, indent=4)
    return True

# --- GERENCIAMENTO DE DADOS ---
def pegar_cliente_ativo():
    if st.session_state.get('usuario_logado') == USUARIO_MASTER:
        # Se o admin não selecionou ninguém ainda, mostra erro ou vazio
        return st.session_state.get('cliente_visualizado', 'admin_sistema')
    else:
        return st.session_state.get('usuario_logado')

def pegar_nome_arquivo():
    cliente = pegar_cliente_ativo()
    return f"dados_{cliente}.json"

def carregar_dados_cliente():
    arquivo = pegar_nome_arquivo()
    if os.path.exists(arquivo):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return DADOS_PADRAO.copy()
    else:
        return DADOS_PADRAO.copy()

def salvar_dados_cliente(dados):
    arquivo = pegar_nome_arquivo()
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# --- PDF ---
def gerar_pdf(lista_carga, nome_espaco, categoria, ocupacao_vol, ocupacao_peso, status, totais, cliente_real):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, txt=f"Relatório - Cliente: {cliente_real.upper()}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, txt=f"Origem/Destino: {nome_espaco} ({categoria})", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, txt=f"Volume: {totais['vol_ocupado']:.2f}m³ / {totais['vol_util']:.2f}m³ ({ocupacao_vol:.1f}%)", ln=True)
    pdf.cell(0, 8, txt=f"Peso: {totais['peso_ocupado']:.0f}kg / {totais['peso_max']:.0f}kg ({ocupacao_peso:.1f}%)", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 15, txt=f"RESULTADO: {status}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(15, 10, "Qtd", 1, align='C')
    pdf.cell(65, 10, "Dimensões", 1, align='C')
    pdf.cell(35, 10, "Vol. Total", 1, align='C')
    pdf.cell(30, 10, "Peso Unit", 1, align='C')
    pdf.cell(35, 10, "Peso Total", 1, align='C')
    pdf.ln()
    pdf.set_font("Arial", size=9)
    for item in lista_carga:
        pdf.cell(15, 10, str(item['Qtd']), 1, align='C')
        pdf.cell(65, 10, item['Dimensões'], 1, align='C')
        pdf.cell(35, 10, f"{item['Vol. Total (m³)']:.3f}", 1, align='C')
        pdf.cell(30, 10, f"{item['Peso Unit (kg)']:.1f}", 1, align='C')
        pdf.cell(35, 10, f"{item['Peso Total (kg)']:.1f}", 1, align='C')
        pdf.ln()
    return bytes(pdf.output(dest='S').encode('latin-1'))

# --- STATES ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_logado'] = None
if 'cliente_visualizado' not in st.session_state:
    st.session_state['cliente_visualizado'] = None

# --- LOGIN LÓGICA BLINDADA ---
def acao_login():
    user = st.session_state.login_user
    pwd = st.session_state.login_pwd
    
    # 1. VERIFICAÇÃO SUPREMA (ADMIN)
    # Verifica primeiro se é o dono, comparando com a variável fixa no código
    if user == USUARIO_MASTER and pwd == SENHA_MASTER_FIXA:
        st.session_state['logado'] = True
        st.session_state['usuario_logado'] = USUARIO_MASTER
        st.session_state['cliente_visualizado'] = None # Admin começa sem selecionar ninguém
        # Cache reset
        st.session_state.banco_dados = {} 
        st.session_state.carga_atual = []
        st.success("Bem-vindo, Chefe!")
        return

    # 2. VERIFICAÇÃO COMUM (CLIENTES)
    usuarios_db = carregar_usuarios()
    if user in usuarios_db and verificar_senha(pwd, usuarios_db[user]):
        st.session_state['logado'] = True
        st.session_state['usuario_logado'] = user
        st.session_state['cliente_visualizado'] = user
        st.session_state.banco_dados = carregar_dados_cliente()
        st.session_state.carga_atual = []
    else:
        st.error("Acesso negado.")

def acao_cadastro():
    novo_user = st.session_state.new_user
    nova_senha = st.session_state.new_pwd
    conf_senha = st.session_state.conf_pwd
    
    # TRAVA 1: Nome proibido
    if novo_user.lower() == USUARIO_MASTER:
        st.error("Este nome de usuário é reservado pelo sistema.")
        return

    if nova_senha != conf_senha:
        st.error("Senhas não conferem.")
        return
    if len(novo_user) < 3:
        st.error("Usuário curto demais.")
        return
        
    if salvar_novo_usuario(novo_user, nova_senha):
        st.success(f"Usuário {novo_user} criado! Faça login.")
    else:
        st.error("Usuário já existe.")

def acao_logout():
    st.session_state['logado'] = False
    st.session_state['usuario_logado'] = None
    st.rerun()

# ================= TELA LOGIN =================
if not st.session_state['logado']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🚛 Portal Logístico")
        st.markdown("---")
        tab1, tab2 = st.tabs(["Entrar", "Nova Conta"])
        with tab1:
            st.text_input("Usuário", key="login_user")
            st.text_input("Senha", type="password", key="login_pwd")
            st.button("Entrar", on_click=acao_login, type="primary")
        with tab2:
            st.text_input("Novo Usuário", key="new_user")
            st.text_input("Nova Senha", type="password", key="new_pwd")
            st.text_input("Confirmar Senha", type="password", key="conf_pwd")
            st.button("Criar Conta", on_click=acao_cadastro)
    st.stop()

# ================= SISTEMA LOGADO =================

with st.sidebar:
    usuario_atual = st.session_state['usuario_logado']
    
    # === PAINEL DO DONO ===
    if usuario_atual == USUARIO_MASTER:
        st.markdown("### 👑 SUPER ADMIN")
        st.success("Modo Deus Ativado")
        
        todos_usuarios = list(carregar_usuarios().keys())
        
        if not todos_usuarios:
            st.warning("Nenhum cliente cadastrado ainda.")
        else:
            # Lógica para manter a seleção
            opcoes_clientes = ["-- Selecione um Cliente --"] + todos_usuarios
            
            idx = 0
            if st.session_state['cliente_visualizado'] in todos_usuarios:
                idx = opcoes_clientes.index(st.session_state['cliente_visualizado'])
                
            cliente_selecionado = st.selectbox("Gerenciar Cliente:", opcoes_clientes, index=idx)
            
            if cliente_selecionado != "-- Selecione um Cliente --":
                if cliente_selecionado != st.session_state['cliente_visualizado']:
                    st.session_state['cliente_visualizado'] = cliente_selecionado
                    st.session_state.banco_dados = carregar_dados_cliente()
                    st.session_state.carga_atual = []
                    st.rerun()
            else:
                st.session_state['cliente_visualizado'] = None
        
        st.markdown("---")
    # ======================
    
    st.write(f"👤 Logado: **{usuario_atual.upper()}**")
    st.button("Sair", on_click=acao_logout)
    
    # Se for admin e não tiver selecionado ninguém, para aqui a sidebar
    if usuario_atual == USUARIO_MASTER and not st.session_state['cliente_visualizado']:
        st.info("👈 Selecione um cliente acima para começar.")
    else:
        # Carrega Menu de Cadastro Normal
        st.markdown("---")
        st.header("⚙️ Cadastro")
        
        if 'banco_dados' not in st.session_state or st.session_state.banco_dados is None:
            st.session_state.banco_dados = carregar_dados_cliente()

        opcoes = ["-- Criar Novo --"] + list(st.session_state.banco_dados.keys())
        item_selecionado = st.selectbox("Item:", opcoes)
        
        with st.form("form_cadastro"):
            if item_selecionado == "-- Criar Novo --":
                st.subheader("Novo")
                nome_input = st.text_input("Nome")
                tipo_input = st.radio("Tipo", ["Veículo", "Armazém"], horizontal=True)
                c_v = st.number_input("C (m)", value=3.00)
                l_v = st.number_input("L (m)", value=2.00)
                a_v = st.number_input("A (m)", value=2.50)
                p_v = st.number_input("Peso (kg)", value=1000)
            else:
                dados = st.session_state.banco_dados[item_selecionado]
                st.subheader("Editar")
                nome_input = st.text_input("Nome", value=item_selecionado, disabled=True)
                cat_atual = dados.get('categoria', 'Veículo')
                tipo_input = st.radio("Tipo", ["Veículo", "Armazém"], index=0 if cat_atual=="Veículo" else 1)
                c_v = st.number_input("C (m)", value=dados['comp'])
                l_v = st.number_input("L (m)", value=dados['larg'])
                a_v = st.number_input("A (m)", value=dados['alt'])
                p_v = st.number_input("Peso (kg)", value=dados['peso_max'])
                
            if st.form_submit_button("Salvar"):
                nova_data = {"categoria": tipo_input, "comp": c_v, "larg": l_v, "alt": a_v, "peso_max": p_v}
                if item_selecionado == "-- Criar Novo --" and nome_input:
                    st.session_state.banco_dados[nome_input] = nova_data
                elif item_selecionado != "-- Criar Novo --":
                    st.session_state.banco_dados[item_selecionado] = nova_data
                salvar_dados_cliente(st.session_state.banco_dados)
                st.rerun()
                
        if item_selecionado != "-- Criar Novo --" and st.button("Excluir"):
            del st.session_state.banco_dados[item_selecionado]
            salvar_dados_cliente(st.session_state.banco_dados)
            st.rerun()

# --- ÁREA PRINCIPAL ---
# Bloqueia tela principal se Admin não escolheu ninguém
if usuario_atual == USUARIO_MASTER and not st.session_state['cliente_visualizado']:
    st.title("Painel Administrativo")
    st.info("Selecione um cliente na barra lateral para visualizar e editar a frota dele.")
    st.stop()

# Daqui pra baixo roda normal (para cliente ou admin vendo cliente)
cliente_ativo = pegar_cliente_ativo()
st.title(f"📦 Gestão de Cargas")
if usuario_atual == USUARIO_MASTER:
    st.warning(f"⚠️ Você está editando os dados de: **{cliente_ativo.upper()}**")

st.markdown("---")

if 'carga_atual' not in st.session_state: st.session_state.carga_atual = []

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("1. Seleção")
    lista = ["-- Digitar Manual --"] + list(st.session_state.banco_dados.keys())
    selecao = st.selectbox("Local de Carga", lista)
    
    if selecao == "-- Digitar Manual --":
        st.info("Modo Rápido")
        comp_f = st.number_input("Comp (m)", value=5.0)
        larg_f = st.number_input("Larg (m)", value=2.5)
        alt_f = st.number_input("Alt (m)", value=2.5)
        peso_f = st.number_input("Max Peso (kg)", value=5000)
        cat_f = "Personalizado"
    else:
        d = st.session_state.banco_dados[selecao]
        comp_f, larg_f, alt_f, peso_f = d['comp'], d['larg'], d['alt'], d['peso_max']
        cat_f = d.get('categoria', 'Veículo')
        st.success(f"Selecionado: {selecao}")

    vol_total = comp_f * larg_f * alt_f
    perda = st.slider("Margem Perda", 0, 30, 15, format="%d%%")
    vol_util = vol_total * (1 - (perda/100))
    st.caption(f"Vol. Útil: {vol_util:.2f} m³ | Peso Max: {peso_f} kg")
    
    st.markdown("#### Adicionar")
    with st.form("add"):
        q = st.number_input("Qtd", 1, value=10)
        p = st.number_input("Peso Unit (kg)", 0.0, value=1.0)
        c1, c2, c3 = st.columns(3)
        cc = c1.number_input("C (cm)", value=40)
        ll = c2.number_input("L (cm)", value=30)
        aa = c3.number_input("A (cm)", value=20)
        if st.form_submit_button("➕ Adicionar"):
            v_u = (cc*ll*aa)/1000000
            st.session_state.carga_atual.append({
                "Qtd": q, "Dimensões": f"{cc}x{ll}x{aa}",
                "Vol. Unit (m³)": v_u, "Vol. Total (m³)": v_u*q,
                "Peso Unit (kg)": p, "Peso Total (kg)": p*q
            })
            st.rerun()

with col2:
    st.subheader("2. Análise")
    if st.session_state.carga_atual:
        for i, item in enumerate(st.session_state.carga_atual):
            c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
            c1.write(f"**{item['Qtd']}x**")
            c2.write(f"{item['Dimensões']}")
            c3.write(f"{item['Vol. Total (m³)']:.2f}")
            if c4.button("❌", key=f"d{i}"):
                st.session_state.carga_atual.pop(i)
                st.rerun()
        
        if st.button("🗑️ Limpar"):
            st.session_state.carga_atual = []
            st.rerun()
            
        st.markdown("---")
        df = pd.DataFrame(st.session_state.carga_atual)
        v_ocup = df["Vol. Total (m³)"].sum()
        p_ocup = df["Peso Total (kg)"].sum()
        pct_v = (v_ocup/vol_util)*100
        pct_p = (p_ocup/peso_f)*100 if peso_f > 0 else 0
        
        cr1, cr2 = st.columns(2)
        cr1.metric("Volume", f"{v_ocup:.2f}/{vol_util:.2f}", delta=f"{vol_util-v_ocup:.2f} livre")
        if pct_v > 100: cr1.error("Estourou!")
        else: cr1.progress(int(pct_v))
        
        cr2.metric("Peso", f"{p_ocup:.0f}/{peso_f:.0f}", delta=f"{peso_f-p_ocup:.0f} livre")
        if pct_p > 100: cr2.error("Estourou!")
        else: cr2.progress(int(pct_p))
        
        status = "APROVADO" if (v_ocup <= vol_util and p_ocup <= peso_f) else "REPROVADO"
        if status == "APROVADO":
            st.success("✅ APROVADO")
            delta = vol_util - v_ocup
            if delta > 0:
                st.info(f"💡 Cabe mais **{delta:.2f} m³**.")
                cols = st.columns(len(st.session_state.carga_atual) if len(st.session_state.carga_atual) > 0 else 1)
                for idx, item in enumerate(st.session_state.carga_atual):
                    if item["Vol. Unit (m³)"] > 0:
                        extra = int(delta // item["Vol. Unit (m³)"])
                        with cols[idx % 4]:
                            if extra > 0: st.markdown(f"**+{extra} cx**\n\n{item['Dimensões']}")
        else:
            st.error("❌ REPROVADO")
            
        if st.button("📄 PDF"):
            totais = {"vol_ocupado": v_ocup, "vol_util": vol_util, "peso_ocupado": p_ocup, "peso_max": peso_f}
            pdf_data = gerar_pdf(st.session_state.carga_atual, selecao, cat_f, pct_v, pct_p, status, totais, cliente_ativo)
            st.download_button("Baixar", pdf_data, "relatorio.pdf", "application/pdf")
    else:
        st.info("Lista vazia.")