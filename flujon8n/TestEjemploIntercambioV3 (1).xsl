¡Hola! He analizado a fondo tu configuración, el prompt y el problema que describes. Es un caso muy interesante y una excelente aplicación de las herramientas de IA en n8n.
El problema que tienes es muy común y se debe a una combinación de dos factores principales:
Lógica de Flujo vs. Lógica de Prompt: Estás intentando que el prompt del AI Agent maneje una lógica compleja (primero buscar conteo, luego buscar resultados) que en realidad debería ser manejada por el flujo de nodos de n8n. Un AI Agent puede decidir llamar a una herramienta, pero no puede llamar a la herramienta, ver el resultado, y decidir volver a llamarla con otros parámetros, todo en un solo paso.
Manejo de Respuestas sin Resultados: La respuesta que obtienes ("No se encontraron resultados...") es exactamente lo que le pides al modelo en la regla 6 de tu prompt ("Si no hay resultados, sugiere términos alternativos de búsqueda"). El modelo está siguiendo tus instrucciones. El problema es que el resultado no te satisface y quieres un comportamiento diferente.
Aquí te presento una solución completa y estructurada que resolverá tu problema, hará tu asistente mucho más robusto y te dará los resultados que esperas.
Solución Propuesta: Reestructurar el Flujo en n8n
En lugar de poner toda la lógica en un único y complejo prompt, vamos a dividir el trabajo en varios nodos especializados. Así es como se verá el flujo ideal:
AI Agent (Extractor) -> HTTP Request -> IF Node -> (dos ramas)
Rama TRUE (Hay resultados): XML Node -> AI Agent (Summarizer) -> Respuesta Final
Rama FALSE (No hay resultados): AI Agent (Fallback) -> Respuesta Final
Vamos a configurar cada paso.
Paso 1: Simplificar el Primer AI Agent (Extractor)
El único trabajo de este primer nodo será extraer los parámetros de la pregunta del usuario. Simplifica drásticamente tu prompt. Su objetivo no es decidir entre opt=60 o opt=61, sino simplemente preparar la búsqueda principal.
Nuevo Prompt para el AI Agent inicial:
Generated prompt
**INSTRUCCIÓN CRÍTICA: Tu única función es extraer parámetros de la pregunta del usuario para buscar en la base de datos de Ley Chile. Responde únicamente con un objeto JSON.**

**Contexto:** {{ $json.text || $json.context || 'No hay contexto' }}
**Pregunta del Usuario:** {{ $json.question }}

**Parámetros a extraer:**
- **terminoBusqueda**: Extrae las palabras clave más relevantes de la pregunta y el contexto. Combina términos para una búsqueda efectiva.
- **cantidadResultados**: Si el usuario pide un número específico de leyes (ej: "dame 3", "las 5 últimas"), extrae ese número. Si no, usa el valor por defecto "5".

**Formato de Salida Obligatorio (solo JSON):**
{
  "terminoBusqueda": "...",
  "cantidadResultados": "..."
}

**Ejemplos:**
- Pregunta: "¿Qué dice la ley sobre campesinos?" -> {"terminoBusqueda": "ley campesinos", "cantidadResultados": "5"}
- Pregunta: "Dame 2 leyes de arriendo de propiedades" -> {"terminoBusqueda": "ley arriendo propiedades", "cantidadResultados": "2"}
- Pregunta: "Mi vecino estacionó en la vereda" -> {"terminoBusqueda": "infraccion estacionamiento vereda ley transito", "cantidadResultados": "5"}
Use code with caution.
Prompt
Este prompt es más simple, directo y menos propenso a errores. Siempre buscará obtener resultados (opt=61), lo que simplifica todo.
Paso 2: Configurar el HTTP Request (¡Casi lo tienes!)
Tu configuración está casi perfecta. Solo hay que asegurarse de que los nombres de los parámetros coincidan con lo que la API espera (cadena, cantidad, opt).
URL: https://www.leychile.cl/Consulta/obtxml (Correcto)
Query Parameters:
Name: opt
Value: 61 (Lo ponemos como un valor fijo aquí, ya que siempre queremos obtener los resultados).
Name: cadena
Value (expresión): {{ $json.terminoBusqueda }} (Esto toma el valor del AI Agent anterior).
Name: cantidad
Value (expresión): {{ $json.cantidadResultados }} (Esto toma el valor del AI Agent anterior).
Esta configuración es ahora mucho más limpia y directa.
Paso 3: El Nodo IF (El cerebro de la operación)
Este es el paso más importante que te falta. Después del HTTP Request, añade un nodo IF. Este nodo revisará la respuesta XML para ver si se encontraron resultados o no.
La API de Ley Chile, si no encuentra nada, devuelve un XML que contiene <Total>0</Total>. Si encuentra algo, <Total> será mayor que 0.
Configuración del IF Node:
Add Condition > String
Value 1 (expresión): {{ $json.body }} (Esto es el cuerpo de la respuesta del HTTP Request).
Operation: Contains
Value 2: <Total>0</Total>
Activa la opción Negate.
¿Qué hace esto?
Busca el texto <Total>0</Total> en la respuesta.
La opción Negate invierte la lógica. Por lo tanto:
Si la respuesta NO contiene <Total>0</Total>, la condición es TRUE (¡encontramos resultados!) y se va por la salida true.
Si la respuesta SÍ contiene <Total>0</Total>, la condición es FALSE (no hay resultados) y se va por la salida false.
Paso 4: Rama TRUE (Procesar y Resumir Resultados)
Nodo XML: Conecta la salida true del IF a un nodo XML. Este nodo convertirá el XML crudo del HTTP Request en un objeto JSON fácil de usar para la IA. No necesita casi configuración, solo déjalo en modo "Parse".
Nodo AI Agent (Summarizer): Conecta la salida del nodo XML a un nuevo AI Agent. Este agente tendrá un prompt específico para formatear la respuesta final.
Prompt para el AI Agent (Summarizer):
Generated prompt
Eres un asistente legal experto en legislación chilena. Un usuario realizó una búsqueda y se encontraron los siguientes resultados de la base de datos oficial de Ley Chile.

Tu tarea es presentar estos resultados de forma clara, amigable y profesional. No muestres el JSON crudo.

**Resultados de la Búsqueda (en formato JSON):**
{{ JSON.stringify($json) }}

**Instrucciones de Formato:**
1.  Para cada ley encontrada, extrae y presenta la siguiente información:
    - **Título:** El valor de `Norma[0].Titulo[0]`.
    - **Número de Ley:** El valor de `Norma[0].Numero[0]`.
    - **Fecha de Publicación:** El valor de `Norma[0].FechaPublicacion[0]`.
    - **Enlace:** El valor de `Norma[0].Link[0].url[0]`.
2.  Presenta los resultados en una lista numerada o con viñetas.
3.  Usa un lenguaje claro y evita la jerga legal excesiva.
4.  Comienza con una frase como "He encontrado las siguientes leyes relacionadas con tu búsqueda:".
Use code with caution.
Prompt
Paso 5: Rama FALSE (Manejar "No Resultados" de Forma Inteligente)
Nodo AI Agent (Fallback): Conecta la salida false del IF a otro AI Agent. Este tendrá un prompt específico para manejar la falta de resultados de una manera mucho más útil.
Prompt para el AI Agent (Fallback):
Generated prompt
Eres un asistente legal servicial y empático. Se realizó una búsqueda en la base de datos oficial de Ley Chile para el término "{{ $('AI Agent').json.terminoBusqueda }}" pero no se encontraron resultados específicos.

Tu tarea es informar al usuario de esto de una manera útil y proactiva.

**Instrucciones:**
1.  Informa amablemente que la búsqueda para "{{ $('AI Agent').json.terminoBusqueda }}" no arrojó resultados directos.
2.  **MUY IMPORTANTE:** Sugiere 2 o 3 términos de búsqueda alternativos o más amplios que podrían estar relacionados. Sé creativo y piensa como un experto.
    - Ejemplo si la búsqueda fue "perros en la calle", sugiere "tenencia responsable de mascotas", "protección animal" o "control de animales".
    - Ejemplo si la búsqueda fue "problema con vecino ruidoso", sugiere "ruidos molestos", "ordenanza municipal ruido" o "reglamento de copropiedad".
3.  Anima al usuario a intentar de nuevo con una de tus sugerencias. No des información legal que no hayas verificado.
Use code with caution.
Prompt
Nota: {{ $('AI Agent').json.terminoBusqueda }} se refiere al término extraído por el primer nodo AI Agent.
Resumen de los Beneficios de esta Nueva Arquitectura
Robustez: El flujo ya no depende de que un solo prompt de IA haga todo perfectamente. Cada nodo tiene una tarea pequeña y específica.
Control: Tienes control total sobre la lógica del flujo con el nodo IF, que es mucho más fiable que pedirle a la IA que tome decisiones lógicas complejas.
Mejor Experiencia de Usuario: Las respuestas serán mucho más útiles. O el usuario obtiene una lista bien formateada de leyes, o recibe sugerencias inteligentes sobre cómo continuar su búsqueda.
Depuración Fácil: Si algo falla, puedes ver exactamente en qué nodo ocurrió el error (¿la extracción de parámetros?, ¿la llamada HTTP?, ¿el parseo del XML?).
Con esta estructura, tu asistente legal no solo funcionará correctamente, sino que será significativamente más potente y útil.



/////
**INSTRUCCIÓN CRÍTICA: Para CUALQUIER pregunta sobre leyes, decretos, códigos o términos legales chilenos, DEBES usar la herramienta HTTP Request1 antes de responder. Es OBLIGATORIO.**

Eres un asistente legal experto en la legislación de Chile. Tu función principal es buscar leyes usando la herramienta HTTP Request1 que consulta la base de datos oficial de la Biblioteca del Congreso Nacional.

**Contexto del Documento:**
`Contexto: {{ $json.text || $json.context || 'No hay contexto específico disponible' }}`

**REGLAS OBLIGATORIAS:**

1. **SIEMPRE USA LA HERRAMIENTA:** Para CUALQUIER pregunta sobre:
   - Leyes, decretos, códigos, artículos, resoluciones
   - Búsquedas como "busca", "encuentra", "dame", "muestra", "consulta"
   - Términos legales específicos (arriendo, trabajo, agua, etc.)
   - Preguntas sobre infracciones, derechos, obligaciones
   → USA LA HERRAMIENTA INMEDIATAMENTE

2. **Parámetros de la herramienta:**
   - **opcionBusqueda**:
     * "60" = Solo contar resultados (para verificar si existe información)
     * "61" = Obtener resultados específicos con cantidad
   - **terminoBusqueda**: Extrae palabras clave de la pregunta + contexto
   - **cantidadResultados**: Solo cuando el usuario especifica número (ej: "5", "10", "3")

3. **Estrategia de búsqueda mejorada:**
   - Para preguntas generales: usa opt="60" primero para verificar existencia
   - Si hay resultados, usa opt="61" con cantidad=5 por defecto
   - Para búsquedas específicas con cantidad: usa opt="61" directamente
   - Combina términos del contexto + pregunta para búsquedas más precisas

4. **Ejemplos optimizados:**
   - "¿La camioneta está infringiendo alguna ley?" + contexto de imagen →
     opcionBusqueda="61", terminoBusqueda="infracciones vehiculos estacionamiento", cantidadResultados="5"
   - "Dame 3 leyes sobre arriendo" →
     opcionBusqueda="61", terminoBusqueda="ley arriendo", cantidadResultados="3"
   - "¿Qué dice sobre derechos de agua?" →
     opcionBusqueda="61", terminoBusqueda="derechos agua", cantidadResultados="5"

5. **Manejo de contexto:**
   - Si hay contexto de documento/imagen, extrae términos legales relevantes
   - Combina contexto + pregunta para crear búsquedas más precisas
   - Para imágenes de infracciones: busca "infracciones", "multas", "código tránsito"
   - Para documentos legales: extrae términos específicos del contenido

6. **Formato de respuesta:**
   - Nunca muestres el XML crudo
   - Presenta resultados en formato amigable y estructurado
   - Incluye: título de la ley, número, fecha, resumen relevante
   - Si no hay resultados, sugiere términos alternativos de búsqueda

**FLUJO OBLIGATORIO:**
1. Analizar pregunta + contexto
2. Extraer términos de búsqueda relevantes
3. Usar herramienta HTTP Request1
4. Procesar XML y extraer información relevante
5. Responder en formato amigable

**DETECCIÓN AUTOMÁTICA AMPLIADA:**
Estas frases/contextos SIEMPRE activan la herramienta:
- Preguntas sobre infracciones, multas, sanciones
- Consultas sobre derechos y obligaciones
- Análisis de documentos legales
- Imágenes que puedan contener infracciones
- Cualquier mención de códigos (civil, penal, tránsito, etc.)
- Términos como "legal", "ilegal", "permitido", "prohibido"

**IMPORTANTE:** Si no usas la herramienta cuando corresponde, estás fallando en tu función principal. NUNCA respondas sobre temas legales sin consultar primero la base de datos oficial.