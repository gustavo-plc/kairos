import streamlit as st
import fitz  # PyMuPDF
import re
import os

# --- LÓGICA DE PROCESSAMENTO (Seu código de cálculo de horas) ---
def processar_pdf(arquivo_pdf):
    doc = fitz.open(stream=arquivo_pdf.read(), filetype="pdf")
    
    padrao_hora = re.compile(r'^(\d{1,2})[h:](\d{2})$')
    padrao_semana = re.compile(r'(?i)\bsem(?:ana)?\s+(\d+)\b')
    
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
                            bbox = span["bbox"]
                            eventos.append({
                                'tipo': 'hora',
                                'page': page_num,
                                'x': (bbox[0] + bbox[2]) / 2,
                                'y': (bbox[1] + bbox[3]) / 2,
                                'color': span["color"],
                                'texto_original': span["text"].strip(),
                                'match_hora': match_hora
                            })

    if not eventos:
        return {}, 0

    max_x = 0
    for e in eventos:
        if e['tipo'] == 'hora' and e['x'] > max_x:
            max_x = e['x']

    tolerancia = 45 
    
    eventos.sort(key=lambda e: (e['page'], e['y']))
    
    semanas_saldo = {}
    semana_atual = 1 
    
    for e in eventos:
        if e['tipo'] == 'semana':
            semana_atual = e['valor']
            if semana_atual not in semanas_saldo:
                semanas_saldo[semana_atual] = 0
                
        elif e['tipo'] == 'hora':
            if e['x'] >= max_x - tolerancia:
                cor_int = e['color']
                r = (cor_int >> 16) & 0xFF
                g = (cor_int >> 8) & 0xFF
                b = cor_int & 0xFF
                
                is_red = r > g + 50 and r > b + 50
                is_green = g > r + 50 and g > b + 50
                
                if is_red or is_green:
                    h, m = int(e['match_hora'].group(1)), int(e['match_hora'].group(2))
                    minutos = h * 60 + m
                    
                    if semana_atual not in semanas_saldo:
                        semanas_saldo[semana_atual] = 0

                    if is_red:
                        if e['texto_original'] in ["7h00", "07h00", "7:00", "07:00"]:
                            continue
                        semanas_saldo[semana_atual] -= minutos
                    elif is_green:
                        semanas_saldo[semana_atual] += minutos

    total_minutos_mes = sum(semanas_saldo.values())
    return semanas_saldo, total_minutos_mes

# --- INTERFACE DO USUÁRIO ---
st.set_page_config(page_title="Calculadora Kairós", layout="centered", page_icon="⏱️")

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
    
    # Inserção da imagem de guia
    nome_imagem = "guia.png" 
    
    if os.path.exists(nome_imagem):
        st.write("---") 
        col_esq, col_img, col_dir = st.columns([1, 2, 1])
        with col_img:
            st.image(nome_imagem, caption="Exemplo visual das configurações corretas.", use_container_width=True)
    else:
        st.warning(f"Aviso para o desenvolvedor: A imagem '{nome_imagem}' não foi encontrada.")

st.divider()

# Upload do arquivo
arquivo_upload = st.file_uploader("Faça o upload do seu espelho de ponto em PDF", type=["pdf"])

if arquivo_upload is not None:
    with st.spinner("Lendo cronologia e calculando saldos..."):
        try:
            semanas_saldo, total_minutos = processar_pdf(arquivo_upload)
            
            st.success("Dados processados com sucesso!")
            st.divider()
            st.subheader("Balanço por Semana")
            
            if not semanas_saldo:
                st.info("Nenhum saldo computável foi encontrado nas colunas. Certifique-se de que seguiu a escala de 30% e marcou 'Apenas Seleção'.")
            else:
                for sem, saldo in sorted(semanas_saldo.items()):
                    saldo_sinal = "+" if saldo >= 0 else "-"
                    h_sem = abs(saldo) // 60
                    m_sem = abs(saldo) % 60
                    cor = "green" if saldo >= 0 else "red"
                    st.markdown(f"**Semana {sem}:** <span style='color:{cor}'>{saldo_sinal}{h_sem:02d}h{m_sem:02d}</span>", unsafe_allow_html=True)
            
            st.divider()
            st.subheader("Saldo Acumulado (Parcial/Total)")
            
            saldo_sinal_final = "+" if total_minutos >= 0 else "-"
            h_final = abs(total_minutos) // 60
            m_final = abs(total_minutos) % 60
            status = "sobrando" if total_minutos >= 0 else "devendo"
            cor_status = "green" if total_minutos >= 0 else "red"
            
            st.write(f"**Valor Final:** {saldo_sinal_final}{h_final:02d}h{m_final:02d}")
            st.markdown(f"**Situação:** Até o momento gerado no documento, você está com <span style='color:{cor_status}'>**{h_final:02d}h{m_final:02d} {status}**</span>.", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo. Verifique se o PDF está correto. Erro técnico: {e}")

st.divider()
st.caption("Nota: O cálculo lê os dados da coluna mais à direita, processa agrupando pelas semanas existentes no documento e ignora registros de 7h00/07:00 em vermelho (teletrabalho).")