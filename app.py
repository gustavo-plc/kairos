import streamlit as st
import fitz  # PyMuPDF
import re
import os
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Extrator Kairós", layout="centered", page_icon="📄")

def processar_pdf(arquivo_pdf):
    doc = fitz.open(stream=arquivo_pdf.read(), filetype="pdf")
    
    padrao_hora = re.compile(r'^(\d{1,2})[h:](\d{2})$')
    padrao_semana = re.compile(r'(?i)sem(?:ana)?\s+(\d+)\b')
    
    eventos = []
    
    for page_num, pagina in enumerate(doc):
        blocos = pagina.get_text("dict").get("blocks", [])
        for bloco in blocos:
            if "lines" in bloco:
                for linha in bloco["lines"]:
                    texto_linha = " ".join([span["text"].strip() for span in linha["spans"]]).lower()
                    
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

def agrupar_por_semana(eventos):
    """
    Usa as coordenadas para ler o PDF de cima para baixo e 
    associar os horários extraídos às suas respectivas semanas.
    """
    # Ordena os eventos por página e depois pela posição vertical (y)
    eventos_ordenados = sorted(eventos, key=lambda e: (e['page'], e['y']))
    
    dados_processados = []
    semana_atual = None
    
    for evento in eventos_ordenados:
        if evento['tipo'] == 'semana':
            semana_atual = f"Semana {evento['valor']}"
        elif evento['tipo'] == 'horario' and semana_atual is not None:
            dados_processados.append({
                'Período': semana_atual,
                'Horários Registrados': evento['valor']
                # Se você extraía um texto específico escrito "Saldo", 
                # a lógica de captura dele entraria aqui.
            })
            
    return pd.DataFrame(dados_processados)

# --- INTERFACE DO USUÁRIO ---
st.title("Sistema de Extração Kairós 📄")

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
    
    nome_imagem = "guia.png" 
    
    if os.path.exists(nome_imagem):
        st.write("---") 
        col_esq, col_img, col_dir = st.columns([1, 2, 1])
        with col_img:
            st.image(nome_imagem, caption="Exemplo visual das configurações corretas.", use_container_width=True)
    else:
        st.warning(f"Aviso para o desenvolvedor: A imagem '{nome_imagem}' não foi encontrada.")

st.divider()

arquivo_upload = st.file_uploader("Faça o upload do seu espelho de ponto gerado em PDF", type=["pdf"])

if arquivo_upload is not None:
    with st.spinner("Processando dados..."):
        try:
            resultados_brutos = processar_pdf(arquivo_upload)
            
            if resultados_brutos:
                # Transforma a lista bruta na tabela agrupada
                df_final = agrupar_por_semana(resultados_brutos)
                
                st.success("Dados processados com sucesso!")
                
                # Exibe a tabela limpa para o cliente
                st.dataframe(df_final, use_container_width=True, hide_index=True)
                
            else:
                st.warning("Nenhum dado foi encontrado. Certifique-se de que seguiu as instruções de escala (30%) e marcou 'Apenas Seleção'.")
        
        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {e}")