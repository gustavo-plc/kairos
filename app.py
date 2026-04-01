import streamlit as st
import fitz  # PyMuPDF
import re
import os # Importado para verificar se a imagem existe

# Configuração da página
st.set_page_config(page_title="Extrator Kairós", layout="centered", page_icon="📄")

def processar_pdf(arquivo_pdf):
    # Abrir o PDF a partir do stream de bytes enviado pelo Streamlit
    doc = fitz.open(stream=arquivo_pdf.read(), filetype="pdf")
    
    padrao_hora = re.compile(r'^(\d{1,2})[h:](\d{2})$')
    padrao_semana = re.compile(r'(?i)sem(?:ana)?\s+(\d+)\b')
    
    eventos = []
    
    for page_num, pagina in enumerate(doc):
        blocos = pagina.get_text("dict").get("blocks", [])
        for bloco in blocos:
            if "lines" in bloco:
                for linha in bloco["lines"]:
                    # Consolida o texto da linha para busca de padrões
                    texto_linha = " ".join([span["text"].strip() for span in linha["spans"]]).lower()
                    
                    # Busca por indicação de semana
                    match_sem = padrao_semana.search(texto_linha)
                    if match_sem:
                        y_centro_linha = (linha["bbox"][1] + linha["bbox"][3]) / 2
                        eventos.append({
                            'tipo': 'semana',
                            'valor': int(match_sem.group(1)),
                            'page': page_num,
                            'y': y_centro_linha,
                            'x': 0
                        })
                    
                    # Busca por horários dentro dos spans da linha
                    for span in linha["spans"]:
                        texto = span["text"].strip().lower()
                        match_hora = padrao_hora.match(texto)
                        if match_hora:
                            y_centro_span = (span["bbox"][1] + span["bbox"][3]) / 2
                            eventos.append({
                                'tipo': 'horario',
                                'valor': texto,
                                'page': page_num,
                                'y': y_centro_span,
                                'x': span["bbox"][0]
                            })
    return eventos

# --- INTERFACE DO USUÁRIO ---
st.title("Sistema de Extração Kairós 📄")

# Seção de orientações para o usuário
with st.expander("📖 Clique aqui para ver como emitir o PDF corretamente", expanded=True):
    st.markdown("""
    Para que o sistema processe seus dados, siga exatamente estes passos no portal Kairós:

    1. **Selecione o mês:** Ao entrar no Kairós, selecione o período desejado.
    2. **Selecione o conteúdo:** Pressione **CTRL + A** (ou **CTRL + T**) para selecionar todo o conteúdo da página.
    3. **Abra a impressão:** Pressione **CTRL + P**.
    4. **Configurações de Impressão:**
        * **Destino:** Salvar como PDF
        * **Página:** Todas
        * **Layout:** Paisagem
    5. **Menu "Mais definições":**
        * **Tamanho do papel:** A4
        * **Margens:** Nenhuma
        * **Escala:** Personalizado (**30%**)
        * **Opções:** Marque obrigatoriamente a caixa **"Apenas seleção"**
    """)
    
    # --- NOVO: INSERÇÃO DA IMAGEM ---
    # Defina aqui o nome do arquivo que você salvou na pasta
    nome_imagem = "guia.png" 
    
    # Verifica se a imagem existe na pasta para não dar erro se você esquecer de colocá-la
    if os.path.exists(nome_imagem):
        st.write("---") # Adiciona uma linha divisória sutil
        st.image(
            nome_imagem, 
            caption="Exemplo visual das configurações corretas na tela de impressão.",
            use_container_width=True # Faz a imagem se ajustar à largura da tela
        )
    else:
        st.warning(f"Aviso para o desenvolvedor: A imagem '{nome_imagem}' não foi encontrada na pasta do projeto.")
    # ---------------------------------

st.divider()

# Upload do arquivo
arquivo_upload = st.file_uploader("Faça o upload do seu espelho de ponto gerado em PDF", type=["pdf"])

if arquivo_upload is not None:
    with st.spinner("Processando dados..."):
        try:
            resultados = processar_pdf(arquivo_upload)
            
            if resultados:
                st.success(f"Sucesso! Foram encontrados {len(resultados)} registros.")
                # Exibe os dados brutos encontrados (você pode melhorar isso depois)
                st.write(resultados)
            else:
                st.warning("Nenhum dado foi encontrado. Certifique-se de que seguiu as instruções de escala (30%) e marcou 'Apenas Seleção'.")
        
        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {e}")