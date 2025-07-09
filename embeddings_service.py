import os
import io
import logging
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import numpy as np
import openai
from PIL import Image
import pytesseract
import PyPDF2
import docx
import json
import tempfile
import base64
from io import BytesIO

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingsService:
    """Servicio para generar embeddings vectoriales de documentos"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", use_openai: bool = False):
        """
        Inicializar servicio de embeddings
        
        Args:
            model_name: Nombre del modelo de sentence-transformers
            use_openai: Si usar OpenAI para embeddings (requiere API key)
        """
        self.use_openai = use_openai
        self.model_name = model_name
        
        if use_openai:
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.embedding_model = "text-embedding-ada-002"
        else:
            # Cargar modelo local de sentence-transformers
            self.model = SentenceTransformer(model_name)
            logger.info(f"Modelo de embeddings cargado: {model_name}")
    
    def extract_text_from_file(self, file_path: str, content_type: str) -> str:
        """
        Extraer texto de diferentes tipos de archivos
        
        Args:
            file_path: Ruta del archivo
            content_type: Tipo de contenido (pdf, image, text, docx)
            
        Returns:
            Texto extraído del archivo
        """
        try:
            if content_type == 'pdf':
                return self._extract_text_from_pdf(file_path)
            elif content_type == 'image':
                return self._extract_text_from_image(file_path)
            elif content_type == 'docx':
                return self._extract_text_from_docx(file_path)
            elif content_type == 'text':
                return self._extract_text_from_text(file_path)
            else:
                logger.warning(f"Tipo de contenido no soportado: {content_type}")
                return ""
        except Exception as e:
            logger.error(f"Error al extraer texto de {file_path}: {e}")
            return ""
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extraer texto de archivo PDF"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error al leer PDF: {e}")
        
        return text.strip()
    
    def _extract_text_from_image(self, file_path: str) -> str:
        """Extraer texto de imagen usando OCR"""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang='spa+eng')
            return text.strip()
        except Exception as e:
            logger.error(f"Error en OCR: {e}")
            return ""
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extraer texto de documento Word"""
        try:
            doc = docx.Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return "\n".join(text)
        except Exception as e:
            logger.error(f"Error al leer DOCX: {e}")
            return ""
    
    def _extract_text_from_text(self, file_path: str) -> str:
        """Extraer texto de archivo de texto plano"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Intentar con diferentes codificaciones
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        return file.read()
                except UnicodeDecodeError:
                    continue
            return ""
        except Exception as e:
            logger.error(f"Error al leer archivo de texto: {e}")
            return ""
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generar embedding vectorial de texto
        
        Args:
            text: Texto para generar embedding
            
        Returns:
            Lista de floats representando el embedding
        """
        if not text.strip():
            logger.warning("Texto vacío para generar embedding")
            return self._get_zero_embedding()
        
        try:
            if self.use_openai:
                return self._generate_openai_embedding(text)
            else:
                return self._generate_local_embedding(text)
        except Exception as e:
            logger.error(f"Error al generar embedding: {e}")
            return self._get_zero_embedding()
    
    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generar embedding usando OpenAI API"""
        try:
            response = openai.Embedding.create(
                model=self.embedding_model,
                input=text
            )
            embedding = response['data'][0]['embedding']
            return embedding
        except Exception as e:
            logger.error(f"Error con OpenAI API: {e}")
            return self._get_zero_embedding()
    
    def _generate_local_embedding(self, text: str) -> List[float]:
        """Generar embedding usando modelo local"""
        try:
            # Limitar longitud del texto para evitar problemas de memoria
            if len(text) > 5000:
                text = text[:5000]
            
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error con modelo local: {e}")
            return self._get_zero_embedding()
    
    def _get_zero_embedding(self) -> List[float]:
        """Obtener embedding de ceros como fallback"""
        # Dimensión estándar para text-embedding-ada-002 o all-MiniLM-L6-v2
        dimension = 1536 if self.use_openai else 384
        return [0.0] * dimension
    
    def generate_embedding_from_file(self, file_path: str, content_type: str) -> Dict[str, Any]:
        """
        Generar embedding de archivo completo
        
        Args:
            file_path: Ruta del archivo
            content_type: Tipo de contenido
            
        Returns:
            Diccionario con embedding y metadata
        """
        # Extraer texto del archivo
        text = self.extract_text_from_file(file_path, content_type)
        
        # Generar embedding
        embedding = self.generate_embedding(text)
        
        # Generar metadata
        metadata = {
            'content_type': content_type,
            'text_length': len(text),
            'embedding_model': self.embedding_model if self.use_openai else self.model_name,
            'extraction_success': bool(text.strip())
        }
        
        return {
            'text': text,
            'embedding': embedding,
            'metadata': metadata
        }
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calcular similaridad coseno entre dos embeddings
        
        Args:
            embedding1: Primer embedding
            embedding2: Segundo embedding
            
        Returns:
            Similaridad coseno (0-1)
        """
        try:
            # Convertir a numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calcular producto punto
            dot_product = np.dot(vec1, vec2)
            
            # Calcular normas
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            # Evitar división por cero
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calcular similaridad coseno
            similarity = dot_product / (norm1 * norm2)
            
            # Normalizar a rango 0-1
            return max(0.0, min(1.0, float(similarity)))
        except Exception as e:
            logger.error(f"Error calculando similaridad: {e}")
            return 0.0
    
    def find_similar_documents(self, query_embedding: List[float], document_embeddings: List[Dict], 
                              threshold: float = 0.7, limit: int = 5) -> List[Dict]:
        """
        Encontrar documentos similares usando embeddings
        
        Args:
            query_embedding: Embedding de la consulta
            document_embeddings: Lista de documentos con embeddings
            threshold: Umbral mínimo de similaridad
            limit: Máximo número de resultados
            
        Returns:
            Lista de documentos similares ordenados por similaridad
        """
        results = []
        
        for doc in document_embeddings:
            if 'embedding' not in doc:
                continue
            
            similarity = self.calculate_similarity(query_embedding, doc['embedding'])
            
            if similarity >= threshold:
                doc_result = doc.copy()
                doc_result['similarity'] = similarity
                results.append(doc_result)
        
        # Ordenar por similaridad descendente
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return results[:limit]
    
    def process_file_for_search(self, file_path: str, content_type: str, 
                               chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
        """
        Procesar archivo dividiéndolo en chunks para mejor búsqueda
        
        Args:
            file_path: Ruta del archivo
            content_type: Tipo de contenido
            chunk_size: Tamaño del chunk en caracteres
            overlap: Solapamiento entre chunks
            
        Returns:
            Lista de chunks con embeddings
        """
        text = self.extract_text_from_file(file_path, content_type)
        
        if not text.strip():
            return []
        
        # Dividir texto en chunks
        chunks = self._create_text_chunks(text, chunk_size, overlap)
        
        # Generar embeddings para cada chunk
        chunk_embeddings = []
        for i, chunk in enumerate(chunks):
            embedding = self.generate_embedding(chunk)
            chunk_embeddings.append({
                'chunk_id': i,
                'text': chunk,
                'embedding': embedding,
                'content_type': content_type
            })
        
        return chunk_embeddings
    
    def _create_text_chunks(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Dividir texto en chunks con solapamiento"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            
            if end == len(text):
                break
                
            start = end - overlap
        
        return chunks
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generar embedding para consulta de búsqueda
        
        Args:
            query: Consulta de búsqueda
            
        Returns:
            Embedding de la consulta
        """
        return self.generate_embedding(query)
    
    def get_embedding_dimension(self) -> int:
        """Obtener dimensión del embedding"""
        return 1536 if self.use_openai else 384
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """
        Validar que el embedding sea válido
        
        Args:
            embedding: Embedding a validar
            
        Returns:
            True si es válido, False si no
        """
        if not isinstance(embedding, list):
            return False
        
        if len(embedding) != self.get_embedding_dimension():
            return False
        
        # Verificar que todos los valores sean números válidos
        for value in embedding:
            if not isinstance(value, (int, float)) or np.isnan(value) or np.isinf(value):
                return False
        
        return True
    
    def normalize_embedding(self, embedding: List[float]) -> List[float]:
        """
        Normalizar embedding para mejor rendimiento
        
        Args:
            embedding: Embedding a normalizar
            
        Returns:
            Embedding normalizado
        """
        try:
            vec = np.array(embedding)
            norm = np.linalg.norm(vec)
            
            if norm == 0:
                return embedding
            
            normalized = vec / norm
            return normalized.tolist()
        except Exception as e:
            logger.error(f"Error normalizando embedding: {e}")
            return embedding