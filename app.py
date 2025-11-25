import streamlit as st
import pandas as pd
from fpdf import FPDF
import json
import os
import hashlib
import time

# --- CONFIGURAÇÃO DA PÁGINA (LINHA OBRIGATÓRIA NO INÍCIO) ---
st.set_page_config(
    page_title="Gestão de espaços",
    page_icon="logo.png", # Ou "🚛" se ainda não subiu a logo
    layout="wide",
    initial_sidebar_state="expanded" # <--- ISSO FORÇA O MENU A APARECER ABERTO
)

# ==============================================================================
# CSS VISUAL + BOTÃO WHATSAPP
# ==============================================================================
st.markdown("""
<style>
/* Fundo Geral */
html, body, .stApp {
    background-color: #08131F !important;
}

/* Botões Padrão */
.stButton>button {
    background-color: #1A87C9 !important;
    color: white !important;
    border-radius: 8px !important;
    border: 1px solid #1A87C9 !important;
}
.stButton>button:hover {
    background-color: #3FAE2A !important;
    border-color: #3FAE2A !important;
}

/* Esconder elementos nativos do Streamlit */
footer, .st-emotion-cache-16txtl3, .st-emotion-cache-q8sbsg { display: none !important; }
#MainMenu, header[data-testid="stHeader"] div:nth-child(3) { display: none !important; }
button[kind="header"] { display: none !important; }
.stApp footer { display: none !important; }

/* === BOTÃO FLUTUANTE DO WHATSAPP === */
.float{
	position:fixed;
	width:60px;
	height:60px;
	bottom:40px;
	right:40px;
	background-color:#25d366;
	color:#FFF;
	border-radius:50px;
	text-align:center;
  font-size:30px;
	box-shadow: 2px 2px 3px #999;
  z-index:100;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  transition: all 0.3s;
}
.float:hover {
    background-color: #128C7E;
    transform: scale(1.1);
    color: white;
}
</style>

<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/font-awesome/4.5.0/css/font-awesome.min.css">
<a href="https://wa.me/5585998374345?text=Olá!%20Vim%20pelo%20Gestão%20de%20espaços%20e%20quero%20saber%20mais." class="float" target="_blank">
<i class="fa fa-whatsapp my-float"></i>
</a>
""", unsafe_allow_html=True)

# ==============================================================================
# SEGURANÇA E CONFIGURAÇÕES
# ==============================================================================
USUARIO_MASTER = "admintabosa"
try:
    SENHA_MASTER_FIXA = st.secrets["admin_password"]
except FileNotFoundError:
    SENHA_MASTER_FIXA = "123456"

ARQUIVO_CREDENCIAIS = 'credenciais.json'
# Dados Padrão VEÍCULOS
DADOS_PADRAO_FROTA = {
    "VUC Padrão": {"categoria": "Veículo", "comp": 4.50, "larg": 2.20, "alt": 2.30, "peso_max": 3500},
}
# Dados Padrão CAIXAS
DADOS_PADRAO_CAIXAS = {
    "Caixa Padrão P": {"comp": 30, "larg": 20, "alt": 20, "peso": 1.5},
    "Caixa Padrão M": {"comp": 50, "larg": 40, "alt": 40, "peso": 5.0},
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
    if usuario.lower() == USUARIO_MASTER: return False 
    usuarios = carregar_usuarios()
    if usuario in usuarios: return False
    usuarios[usuario] = criptografar_senha(senha)
    with open(ARQUIVO_CREDENCIAIS, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, indent=4)
    return True

# === FUNÇÕES DE ADMINISTRAÇÃO ===
def atualizar_senha_usuario(usuario, nova_senha):
    usuarios = carregar_usuarios()
    if usuario in usuarios:
        usuarios[usuario] = criptografar_senha(nova_senha)
        with open(ARQUIVO_CREDENCIAIS, 'w', encoding='utf-8') as f:
            json.dump(usuarios, f, indent=4)
        return True
    return False

def excluir_usuario_completo(usuario):
    # 1. Remove do arquivo de credenciais
    usuarios = carregar_usuarios()
    if usuario in usuarios:
        del usuarios[usuario]
        with open(ARQUIVO_CREDENCIAIS, 'w', encoding='utf-8') as f:
            json.dump(usuarios, f, indent=4)
        
        # 2. Remove arquivos de dados para limpar o servidor
        try: os.remove(f"dados_{usuario}.json")
        except: pass
        try: os.remove(f"caixas_{usuario}.json")
        except: pass
        
        return True
    return False

# --- GERENCIAMENTO DE ARQUIVOS (FROTA E CAIXAS) ---
def pegar_cliente_ativo():
    if st.session_state.get('usuario_logado') == USUARIO_MASTER:
        return st.session_state.get('cliente_visualizado', 'admin_sistema')
    else:
        return st.session_state.get('usuario_logado')

# 1. FROTA (Veículos/Armazéns)
def pegar_arquivo_frota():
    return f"dados_{pegar_cliente_ativo()}.json"

def carregar_dados_frota():
    arquivo = pegar_arquivo_frota()
    if os.path.exists(arquivo):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f: return json.load(f)
        except: return DADOS_PADRAO_FROTA.copy()
    return DADOS_PADRAO_FROTA.copy()

def salvar_dados_frota(dados):
    with open(pegar_arquivo_frota(), 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# 2. CAIXAS (Produtos)
def pegar_arquivo_caixas():
    return f"caixas_{pegar_cliente_ativo()}.json"

def carregar_dados_caixas():
    arquivo = pegar_arquivo_caixas()
    if os.path.exists(arquivo):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f: return json.load(f)
        except: return DADOS_PADRAO_CAIXAS.copy()
    return DADOS_PADRAO_CAIXAS.copy()

def salvar_dados_caixas(dados):
    with open(pegar_arquivo_caixas(), 'w', encoding='utf-8') as f:
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

# --- SESSÃO E LOGIN ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
    st.session_state['usuario_logado'] = None
if 'cliente_visualizado' not in st.session_state:
    st.session_state['cliente_visualizado'] = None

# Ações de Login
def acao_login():
    user = st.session_state.login_user
    pwd = st.session_state.login_pwd
    
    if user == USUARIO_MASTER and pwd == SENHA_MASTER_FIXA:
        st.session_state['logado'] = True
        st.session_state['usuario_logado'] = USUARIO_MASTER
        st.session_state['cliente_visualizado'] = None
        st.session_state.banco_dados = {} 
        st.session_state.banco_caixas = {}
        st.session_state.carga_atual = []
        return

    usuarios_db = carregar_usuarios()
    if user in usuarios_db and verificar_senha(pwd, usuarios_db[user]):
        st.session_state['logado'] = True
        st.session_state['usuario_logado'] = user
        st.session_state['cliente_visualizado'] = user
        # Carrega dados específicos do cliente
        st.session_state.banco_dados = carregar_dados_frota()
        st.session_state.banco_caixas = carregar_dados_caixas()
        st.session_state.carga_atual = []
    else:
        st.error("Acesso negado.")

def acao_cadastro():
    novo_user = st.session_state.new_user
    nova_senha = st.session_state.new_pwd
    conf_senha = st.session_state.conf_pwd
    if novo_user.lower() == USUARIO_MASTER:
        st.toast("Nome reservado.", icon="🚫")
        return
    if nova_senha != conf_senha:
        st.toast("Senhas não conferem.", icon="❌")
        return
    if len(novo_user) < 3:
        st.toast("Usuário curto.", icon="⚠️")
        return
    if salvar_novo_usuario(novo_user, nova_senha):
        st.toast(f"Usuário {novo_user} criado com sucesso!", icon="✅")
        time.sleep(1.5) # Pausa para ler a mensagem
    else:
        st.toast("Usuário já existe.", icon="❌")

def acao_logout():
    st.session_state['logado'] = False
    st.session_state['usuario_logado'] = None
    # Removido st.rerun() para evitar erro de callback

# ================= TELA LOGIN =================
if not st.session_state['logado']:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🚛 Gestão de espaços")
        # st.markdown("---")
        # --- AQUI ESTÁ A FRASE QUE VENDE ---
        st.markdown("""
        <div style='background-color: #1A2634; padding: 15px; border-radius: 10px; border-left: 5px solid #3FAE2A; margin-bottom: 20px;'>
        <p style='color: white; margin: 0; font-size: 16px;'>
        <b>Pare de perder viagem.</b><br>
        Calcule a cubagem da sua carga em segundos, evite prejuízos e gere relatórios profissionais.
        </p>
        </div>
        """, unsafe_allow_html=True)
        # -----------------------------------
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

# Inicializa variáveis se não existirem
if 'banco_dados' not in st.session_state or st.session_state.banco_dados is None:
    st.session_state.banco_dados = carregar_dados_frota()
if 'banco_caixas' not in st.session_state or st.session_state.banco_caixas is None:
    st.session_state.banco_caixas = carregar_dados_caixas()

with st.sidebar:
    usuario_atual = st.session_state['usuario_logado']
    
    # === PAINEL DO DONO ===
    if usuario_atual == USUARIO_MASTER:
        st.markdown("### 👑 SUPER ADMIN")
        todos_usuarios = list(carregar_usuarios().keys())
        if not todos_usuarios:
            st.warning("Sem clientes.")
        else:
            opcoes_clientes = ["-- Selecione --"] + todos_usuarios
            idx = 0
            if st.session_state['cliente_visualizado'] in todos_usuarios:
                idx = opcoes_clientes.index(st.session_state['cliente_visualizado'])
            
            cliente_selecionado = st.selectbox("Cliente:", opcoes_clientes, index=idx)
            
            if cliente_selecionado != "-- Selecione --":
                if cliente_selecionado != st.session_state['cliente_visualizado']:
                    st.session_state['cliente_visualizado'] = cliente_selecionado
                    st.session_state.banco_dados = carregar_dados_frota()
                    st.session_state.banco_caixas = carregar_dados_caixas()
                    st.session_state.carga_atual = []
                    st.rerun()
                
                # ==== AQUI ESTÁ A NOVA ÁREA DE GESTÃO DE CONTA ====
                with st.expander("⚙️ Gerenciar Conta do Cliente"):
                    st.markdown(f"**Cliente:** {cliente_selecionado}")
                    
                    # 1. TROCAR SENHA
                    nova_senha_admin = st.text_input("Nova Senha:", type="password", key="adm_new_pass")
                    if st.button("🔄 Atualizar Senha"):
                        if len(nova_senha_admin) > 0:
                            if atualizar_senha_usuario(cliente_selecionado, nova_senha_admin):
                                st.toast("Senha alterada com sucesso!", icon="✅")
                            else:
                                st.error("Erro ao alterar.")
                        else:
                            st.warning("Digite uma senha.")
                    
                    st.markdown("---")
                    
                    # 2. EXCLUIR CLIENTE
                    st.markdown("🚨 **Zona de Perigo**")
                    confirmar_exclusao = st.checkbox("Confirmar exclusão definitiva")
                    if st.button("🗑️ EXCLUIR CLIENTE"):
                        if confirmar_exclusao:
                            if excluir_usuario_completo(cliente_selecionado):
                                st.toast(f"Cliente {cliente_selecionado} removido!", icon="🗑️")
                                time.sleep(1.5) # Pausa dramática
                                st.session_state['cliente_visualizado'] = None
                                st.rerun()
                            else:
                                st.error("Erro ao excluir.")
                        else:
                            st.warning("Marque a caixa acima para confirmar.")
                # ===================================================

            else:
                st.session_state['cliente_visualizado'] = None
        st.markdown("---")
    
    st.write(f"👤 **{usuario_atual.upper()}**")
    st.button("Sair", on_click=acao_logout)
    
    if usuario_atual == USUARIO_MASTER and not st.session_state['cliente_visualizado']:
        st.info("👈 Selecione um cliente.")
    else:
        # ==========================================
        # 1. CADASTRO DE FROTA / ARMAZÉM
        # ==========================================
        st.markdown("### 🚛 Frota e Espaços")
        opcoes_frota = ["-- Novo Veículo --"] + list(st.session_state.banco_dados.keys())
        item_frota = st.selectbox("Editar Veículo:", opcoes_frota)
        
        with st.form("form_frota"):
            if item_frota == "-- Novo Veículo --":
                nome_f = st.text_input("Nome (ex: Truck)")
                tipo_f = st.radio("Tipo", ["Veículo", "Armazém"], horizontal=True)
                c_f = st.number_input("C (m)", 0.00)
                l_f = st.number_input("L (m)", 0.00)
                a_f = st.number_input("A (m)", 0.00)
                p_f = st.number_input("Peso (kg)", 0000)
            else:
                d = st.session_state.banco_dados[item_frota]
                nome_f = st.text_input("Nome", value=item_frota, disabled=True)
                cat_atual = d.get('categoria', 'Veículo')
                tipo_f = st.radio("Tipo", ["Veículo", "Armazém"], index=0 if cat_atual=="Veículo" else 1)
                c_f = st.number_input("C (m)", value=d['comp'])
                l_f = st.number_input("L (m)", value=d['larg'])
                a_f = st.number_input("A (m)", value=d['alt'])
                p_f = st.number_input("Peso (kg)", value=d['peso_max'])
            
            if st.form_submit_button("Salvar Veículo"):
                novo_dado = {"categoria": tipo_f, "comp": c_f, "larg": l_f, "alt": a_f, "peso_max": p_f}
                if item_frota == "-- Novo Veículo --" and nome_f:
                    st.session_state.banco_dados[nome_f] = novo_dado
                elif item_frota != "-- Novo Veículo --":
                    st.session_state.banco_dados[item_frota] = novo_dado
                salvar_dados_frota(st.session_state.banco_dados)
                st.toast("Veículo Salvo com Sucesso!", icon="✅")
                time.sleep(0.5) # Pausa pequena
                st.rerun()
        
        if item_frota != "-- Novo Veículo --" and st.button("Excluir Veículo"):
            del st.session_state.banco_dados[item_frota]
            salvar_dados_frota(st.session_state.banco_dados)
            st.toast("Veículo Excluído!", icon="🗑️")
            time.sleep(0.5)
            st.rerun()

        st.markdown("---")

        # ==========================================
        # 2. CADASTRO DE CAIXAS / PRODUTOS
        # ==========================================
        st.markdown("### 📦 Minhas Caixas")
        opcoes_caixa = ["-- Nova Caixa --"] + list(st.session_state.banco_caixas.keys())
        item_caixa = st.selectbox("Editar Caixa:", opcoes_caixa)

        with st.form("form_caixa"):
            if item_caixa == "-- Nova Caixa --":
                nome_c = st.text_input("Nome do Produto/Caixa")
                # Padrão para nova caixa
                comp_c = st.number_input("Comp (cm)", value=40)
                larg_c = st.number_input("Larg (cm)", value=30)
                alt_c = st.number_input("Alt (cm)", value=20)
                peso_c = st.number_input("Peso Unit (kg)", value=1.0)
            else:
                dc = st.session_state.banco_caixas[item_caixa]
                nome_c = st.text_input("Nome", value=item_caixa, disabled=True)
                comp_c = st.number_input("Comp (cm)", value=dc['comp'])
                larg_c = st.number_input("Larg (cm)", value=dc['larg'])
                alt_c = st.number_input("Alt (cm)", value=dc['alt'])
                peso_c = st.number_input("Peso Unit (kg)", value=dc['peso'])

            if st.form_submit_button("Salvar Caixa"):
                nova_caixa = {"comp": comp_c, "larg": larg_c, "alt": alt_c, "peso": peso_c}
                if item_caixa == "-- Nova Caixa --" and nome_c:
                    st.session_state.banco_caixas[nome_c] = nova_caixa
                elif item_caixa != "-- Nova Caixa --":
                    st.session_state.banco_caixas[item_caixa] = nova_caixa
                salvar_dados_caixas(st.session_state.banco_caixas)
                st.toast("Caixa Salva com Sucesso!", icon="✅")
                time.sleep(0.5)
                st.rerun()

        if item_caixa != "-- Nova Caixa --" and st.button("Excluir Caixa"):
            del st.session_state.banco_caixas[item_caixa]
            salvar_dados_caixas(st.session_state.banco_caixas)
            st.toast("Caixa Excluída!", icon="🗑️")
            time.sleep(0.5)
            st.rerun()

# --- ÁREA PRINCIPAL ---
if usuario_atual == USUARIO_MASTER and not st.session_state['cliente_visualizado']:
    st.title("Painel Administrativo")
    st.info("Selecione um cliente.")
    st.stop()

cliente_ativo = pegar_cliente_ativo()
st.title(f"📦 Gestão de Cargas")
if usuario_atual == USUARIO_MASTER:
    st.warning(f"⚠️ Editando: **{cliente_ativo.upper()}**")

st.markdown("---")

if 'carga_atual' not in st.session_state: st.session_state.carga_atual = []

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("1. Seleção")
    lista = ["-- Digitar Manual --"] + list(st.session_state.banco_dados.keys())
    selecao = st.selectbox("Veículo/Armazém", lista)
    
    if selecao == "-- Digitar Manual --":
        st.info("Modo Manual")
        comp_f = st.number_input("Comp (m)", 5.0)
        larg_f = st.number_input("Larg (m)", 2.5)
        alt_f = st.number_input("Alt (m)", 2.5)
        peso_f = st.number_input("Peso Max (kg)", 5000)
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
    
    st.markdown("#### Adicionar Carga")
    
    # SELETOR DE CAIXA SALVA (Para preencher automático)
    lista_caixas_salvas = ["-- Manual --"] + list(st.session_state.banco_caixas.keys())
    box_selecionada = st.selectbox("Usar Item Salvo:", lista_caixas_salvas)

    # Define valores padrão (inputs)
    def_c, def_l, def_a, def_p = 40, 30, 20, 1.0
    
    if box_selecionada != "-- Manual --":
        d_box = st.session_state.banco_caixas[box_selecionada]
        def_c = d_box['comp']
        def_l = d_box['larg']
        def_a = d_box['alt']
        def_p = d_box['peso']

    with st.form("add"):
        q = st.number_input("Qtd", 1, value=10)
        # Se escolheu caixa salva, usa os valores dela como 'value'
        # Se for manual, o usuário edita livremente
        p = st.number_input("Peso Unit (kg)", 0.0, value=float(def_p))
        
        c1, c2, c3 = st.columns(3)
        cc = c1.number_input("C (cm)", value=int(def_c))
        ll = c2.number_input("L (cm)", value=int(def_l))
        aa = c3.number_input("A (cm)", value=int(def_a))
        
        if st.form_submit_button("➕ Adicionar"):
            v_u = (cc*ll*aa)/1000000
            # Nome do item na lista
            desc = box_selecionada if box_selecionada != "-- Manual --" else f"{cc}x{ll}x{aa}"
            
            st.session_state.carga_atual.append({
                "Qtd": q, 
                "Dimensões": desc, # Mostra o nome do produto ou as medidas
                "Medidas Reais": f"{cc}x{ll}x{aa}",
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