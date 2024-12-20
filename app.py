import streamlit as st
import pandas as pd

st.set_page_config(
    layout="wide"
)

st.markdown(
    r"""
    <style>
    .stAppDeployButton {
            visibility: hidden;
        }
    </style>
    """, unsafe_allow_html=True
)

st.markdown(
    r"""
    <style>
    .stMainMenu {
            visibility: hidden;
        }
    </style>
    """, unsafe_allow_html=True
)

conn = st.connection("mysql", type="sql", pool_size=20, pool_recycle=3600, pool_pre_ping=True)
df_produtos_lote = conn.query("""
SELECT 
  CodEmpresa, CodProduto, Lote
FROM produtoslotes
GROUP BY CodEmpresa, Lote;                
                """)

sql_lotes = ("""
SELECT * FROM (
	SELECT 
	  PL.CodOrigem,
	  PL.Origem,
	  PL.Lote,
	  PL.TipoMovimentacao,
	  PL.DataMovimentacao,
	  PL.HoraMovimentacao,
	  PL.DataFabricacao,
	  PL.DataValidade,
	  PL.Quantidade,
	  PL.DataHoraInsert,
	  (SELECT SUM(CASE WHEN SUBPL.TipoMovimentacao = 'E' THEN SUBPL.Quantidade ELSE -SUBPL.Quantidade END)
	   FROM produtoslotes AS SUBPL
	   WHERE SUBPL.CodProduto = PL.CodProduto
	     AND SUBPL.Lote = PL.Lote
	     AND SUBPL.DataHoraInsert <= PL.DataHoraInsert
	     AND SUBPL.CodEmpresa = :CodEmpresa
	  ) AS Saldo,
	  P.Codigo AS ProdutoCodigo,
	  P.Descricao AS ProdutoDescricao,
	  P.Unidade AS ProdutoUnidade,
	  E.RazaoSocial AS EmpresaRazaoSocial,
	  E.NomeFantasia AS EmpresaNomeFantasia,
	  E.Cnpj AS EmpresaCnpj,
	  f_nome_participante_documento(PL.Origem,  
	    IF(PL.Origem IN ('AJEN', 'AJSA'), PL.CodEstoque, PL.CodOrigem)
	  ) AS Nome,
	  f_numero_documento_fiscal(
	    IF(PL.Origem = 'VE', (SELECT vendas.DfTipo FROM vendas WHERE Codigo = PL.CodOrigem), PL.Origem), 
	    IF(PL.Origem = 'VE', (SELECT vendas.DfCodigo FROM vendas WHERE Codigo = PL.CodOrigem), PL.CodOrigem)
	  ) AS NumeroDocumentoFiscal 
	FROM 
	  produtoslotes AS PL
	  LEFT JOIN produtos AS P ON (PL.CodProduto = P.Codigo)
	  LEFT JOIN empresa AS E ON (PL.CodEmpresa = E.Codigo)
	WHERE 
	  PL.CodProduto = :CodProduto
	  AND PL.Lote = :Lote
	  AND PL.CodEmpresa = :CodEmpresa
	ORDER BY PL.DataHoraInsert
) AS T1
ORDER BY T1.DataHoraInsert DESC
LIMIT 1                      
                      """)


df = pd.DataFrame()
for i in range(len(df_produtos_lote)):   
  df_lote_saldo = conn.query(sql_lotes, params={
      "CodProduto": df_produtos_lote["CodProduto"].iloc[i], 
      "Lote": df_produtos_lote["Lote"].iloc[i],
      "CodEmpresa": df_produtos_lote["CodEmpresa"].iloc[i]})
  
  if df_lote_saldo["Saldo"][0] < 0:
    df = pd.concat([df, df_lote_saldo])
    
colunas = ["ProdutoCodigo", "ProdutoDescricao", "Lote", "Saldo", "DataFabricacao", "DataValidade", "EmpresaNomeFantasia"]     
df = df[colunas].copy()
df = df.sort_values(["EmpresaNomeFantasia", "ProdutoCodigo"])
df = df.reset_index(drop=True)


if st.button("Atualizar"):
    st.rerun()
    
st.markdown( f"***Registros: {len(df)}***")

st.dataframe(df, 
             hide_index=True,
             use_container_width=True,
             column_config={
                "DataFabricacao": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "DataValidade": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "Saldo": st.column_config.NumberColumn(format="%.2f")
             }
             )
