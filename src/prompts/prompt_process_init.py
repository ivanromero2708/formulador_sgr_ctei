USER_PROMPT_TEMPLATE = """
🗂️ **Proyecto Formulación CTeI · Extracción de sección TDR**

Vamos a desarrollar **la sección <{seccion_tdr}>** de los Términos de Referencia (TDR).

📂 **Vector store**:  
• Ruta local = {persist_path}  
(Contiene embeddings de todo el documento; usa retrieval sobre ese almacén).

🎯 **Qué debes lograr**  
1. Localizar, recuperar y entregar **el texto íntegro y sin truncar** que corresponde a <{seccion_tdr}>.  
2. Justificar la selección con *scores* o breves notas de relevancia (<50 car.) por fragmento.  
3. Generar, en paralelo, _insights_ clave (máx. 200 palabras) que resuman la sección para consumo humano.

🔍 **Guía de búsqueda**  
{definicion}

⚙️ **Metodología obligatoria**  
• Ejecuta **≥ 7 ciclos iterativos**:  
  - En cada ciclo, crea 1-2 queries específicas → recupera N fragmentos → analiza → ajusta queries.  
• Usa **RAG**: retrieval del vector store → razonamiento → generación.  
• Prioriza encabezados, tablas o listas que coincidan con palabras clave y señales contextuales.  
• Si aparecen varias versiones, elige la más extensa y actual.

📑 **Formato de salida (texto plano extraido directamente del documento)**  
```plain_text
<texto_extraido>
```
⚠️ Reglas
• No inventes contenido ni edites el texto original.
• No incluyas fragmentos fuera de la sección objetivo.
• Responde solo con el bloque texto_extraido; nada de explicaciones adicionales.
"""