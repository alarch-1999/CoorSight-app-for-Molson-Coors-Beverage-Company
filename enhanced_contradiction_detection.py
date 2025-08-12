# Enhanced Contradiction Detection System for CoorSight
import re
import spacy
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

# Try to load spaCy model, fallback if not available
try:
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except OSError:
    SPACY_AVAILABLE = False
    print("spaCy model not found. Install with: python -m spacy download en_core_web_sm")

# Try to load sentence transformer model
try:
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    SENTENCE_TRANSFORMER_AVAILABLE = True
except Exception:
    SENTENCE_TRANSFORMER_AVAILABLE = False
    print("Sentence Transformers not available. Install with: pip install sentence-transformers")

@dataclass
class Contradiction:
    """Data class for storing contradiction information"""
    type: str
    description: str
    doc1_info: Dict[str, Any]
    doc2_info: Dict[str, Any]
    severity: str
    confidence: float
    entities_involved: List[str]
    context: Dict[str, str]
    suggestion: str = ""

class EnhancedContradictionDetector:
    """Enhanced contradiction detection system"""
    
    def __init__(self):
        self.contradiction_patterns = self._initialize_patterns()
        self.entity_cache = {}
        self.sentence_cache = {}
        
    def _initialize_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize comprehensive contradiction detection patterns"""
        return {
            'temporal': [
                {
                    'pattern': r'(?:deadline|due|complete|finish)(?:s|d)?\s+(?:is|by|on|in)\s+([^.]+)',
                    'context': 'deadline',
                    'weight': 0.9
                },
                {
                    'pattern': r'(?:start|begin|commence)(?:s|ed)?\s+(?:on|in|at)\s+([^.]+)',
                    'context': 'start_date',
                    'weight': 0.9
                },
                {
                    'pattern': r'(?:duration|timeline|timeframe)\s+(?:is|of)\s+([^.]+)',
                    'context': 'duration',  
                    'weight': 0.8
                }
            ],
            'numerical': [
                {
                    'pattern': r'(?:budget|cost|price|amount)\s+(?:is|of)\s+\$?([\d,]+\.?\d*)',
                    'context': 'budget',
                    'weight': 0.95
                },
                {
                    'pattern': r'(?:quantity|amount|number|count)\s+(?:is|of)\s+([\d,]+)',
                    'context': 'quantity',
                    'weight': 0.8
                },
                {
                    'pattern': r'(?:percentage|percent|%)\s+(?:is|of)\s+([\d.]+)%?',
                    'context': 'percentage',
                    'weight': 0.85
                }
            ],
            'factual': [
                {
                    'pattern': r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:is|was|will be)\s+([^.]+)',
                    'context': 'entity_attribute',
                    'weight': 0.7
                },
                {
                    'pattern': r'(?:located|based|situated)\s+(?:in|at)\s+([^.]+)',
                    'context': 'location',
                    'weight': 0.8
                }
            ],
            'status': [
                {
                    'pattern': r'(?:status|state|condition)\s+(?:is|was)\s+([^.]+)',
                    'context': 'status',
                    'weight': 0.75
                },
                {
                    'pattern': r'(?:completed|finished|done|pending|in progress)',
                    'context': 'completion_status',
                    'weight': 0.8
                }
            ]
        }
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text using spaCy"""
        if not SPACY_AVAILABLE:
            # Fallback to simple regex-based entity extraction
            return self._extract_entities_fallback(text)
        
        if text in self.entity_cache:
            return self.entity_cache[text]
        
        doc = nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': 0.8  # Default confidence for spaCy entities
            })
        
        self.entity_cache[text] = entities
        return entities
    
    def _extract_entities_fallback(self, text: str) -> List[Dict[str, Any]]:
        """Fallback entity extraction using regex"""
        entities = []
        
        # Extract potential person names (Title Case words)
        person_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        for match in re.finditer(person_pattern, text):
            entities.append({
                'text': match.group(),
                'label': 'PERSON',
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.6
            })
        
        # Extract dates
        date_pattern = r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})\b'
        for match in re.finditer(date_pattern, text):
            entities.append({
                'text': match.group(),
                'label': 'DATE',
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.7
            })
        
        # Extract monetary amounts
        money_pattern = r'\$[\d,]+\.?\d*'
        for match in re.finditer(money_pattern, text):
            entities.append({
                'text': match.group(),
                'label': 'MONEY',
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.9
            })
        
        return entities
    
    def get_sentence_embeddings(self, sentences: List[str]) -> np.ndarray:
        """Get sentence embeddings for semantic similarity"""
        if not SENTENCE_TRANSFORMER_AVAILABLE:
            # Fallback to simple word overlap similarity
            return self._simple_similarity_matrix(sentences)
        
        cache_key = str(hash(tuple(sentences)))
        if cache_key in self.sentence_cache:
            return self.sentence_cache[cache_key]
        
        embeddings = sentence_model.encode(sentences)
        self.sentence_cache[cache_key] = embeddings
        return embeddings
    
    def _simple_similarity_matrix(self, sentences: List[str]) -> np.ndarray:
        """Fallback similarity calculation using word overlap"""
        n = len(sentences)
        similarity_matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    similarity_matrix[i][j] = 1.0
                else:
                    words_i = set(sentences[i].lower().split())
                    words_j = set(sentences[j].lower().split())
                    
                    if len(words_i | words_j) == 0:
                        similarity_matrix[i][j] = 0.0
                    else:
                        similarity_matrix[i][j] = len(words_i & words_j) / len(words_i | words_j)
        
        return similarity_matrix
    
    def detect_semantic_contradictions(self, documents: List[Dict[str, Any]]) -> List[Contradiction]:
        """Detect semantic contradictions using sentence embeddings"""
        contradictions = []
        
        if len(documents) < 2:
            return contradictions
        
        # Extract sentences from all documents
        all_sentences = []
        sentence_doc_map = []
        
        for doc_idx, doc in enumerate(documents):
            if doc.get('has_error', False):
                continue
                
            text = doc.get('text', '')
            sentences = [s.strip() for s in text.split('.') if s.strip() and len(s.strip()) > 10]
            
            for sentence in sentences:
                all_sentences.append(sentence)
                sentence_doc_map.append({
                    'doc_idx': doc_idx,
                    'doc_id': doc['id'],
                    'doc_name': doc['name'],
                    'sentence': sentence
                })
        
        if len(all_sentences) < 2:
            return contradictions
        
        # Get similarity matrix
        embeddings = self.get_sentence_embeddings(all_sentences)
        
        if SENTENCE_TRANSFORMER_AVAILABLE:
            similarity_matrix = cosine_similarity(embeddings)
        else:
            similarity_matrix = embeddings
        
        # Find potentially contradictory sentences
        for i in range(len(all_sentences)):
            for j in range(i + 1, len(all_sentences)):
                # Skip if same document
                if sentence_doc_map[i]['doc_idx'] == sentence_doc_map[j]['doc_idx']:
                    continue
                
                similarity = similarity_matrix[i][j]
                
                # Check for high similarity with potential negation
                if 0.6 <= similarity <= 0.85:  # Similar topics but might be contradictory
                    sent1 = all_sentences[i].lower()
                    sent2 = all_sentences[j].lower()
                    
                    # Check for negation patterns
                    negation_indicators = [
                        ('not', ''), ('no', 'yes'), ('cannot', 'can'), ('will not', 'will'),
                        ('is not', 'is'), ('are not', 'are'), ('was not', 'was'),
                        ('never', 'always'), ('none', 'all'), ('impossible', 'possible')
                    ]
                    
                    contradiction_found = False
                    for neg, pos in negation_indicators:
                        if (neg in sent1 and pos in sent2) or (pos in sent1 and neg in sent2):
                            contradiction_found = True
                            break
                    
                    if contradiction_found:
                        contradictions.append(Contradiction(
                            type='semantic',
                            description='Semantic contradiction detected',
                            doc1_info={
                                'id': sentence_doc_map[i]['doc_id'],
                                'name': sentence_doc_map[i]['doc_name'],
                                'text': all_sentences[i]
                            },
                            doc2_info={
                                'id': sentence_doc_map[j]['doc_id'],
                                'name': sentence_doc_map[j]['doc_name'],
                                'text': all_sentences[j]
                            },
                            severity='High',
                            confidence=0.8,
                            entities_involved=[],
                            context={
                                'similarity_score': similarity,
                                'type': 'negation_pattern'
                            },
                            suggestion='Review these statements for potential contradictions'
                        ))
        
        return contradictions
    
    def detect_pattern_contradictions(self, documents: List[Dict[str, Any]]) -> List[Contradiction]:
        """Detect contradictions using pattern matching"""
        contradictions = []
        
        # Extract patterns from all documents
        doc_patterns = {}
        
        for doc in documents:
            if doc.get('has_error', False):
                continue
            
            doc_id = doc['id']
            text = doc.get('text', '')
            doc_patterns[doc_id] = {
                'doc': doc,
                'patterns': self._extract_patterns(text)
            }
        
        # Compare patterns across documents
        doc_ids = list(doc_patterns.keys())
        
        for i in range(len(doc_ids)):
            for j in range(i + 1, len(doc_ids)):
                doc1_id, doc2_id = doc_ids[i], doc_ids[j]
                doc1_data = doc_patterns[doc1_id]
                doc2_data = doc_patterns[doc2_id]
                
                # Compare each pattern type
                for pattern_type in self.contradiction_patterns.keys():
                    patterns1 = doc1_data['patterns'].get(pattern_type, [])
                    patterns2 = doc2_data['patterns'].get(pattern_type, [])
                    
                    for p1 in patterns1:
                        for p2 in patterns2:
                            if self._are_contradictory(p1, p2, pattern_type):
                                contradictions.append(Contradiction(
                                    type=pattern_type,
                                    description=f'{pattern_type.title()} contradiction detected',
                                    doc1_info={
                                        'id': doc1_id,
                                        'name': doc1_data['doc']['name'],
                                        'text': p1['context'],
                                        'value': p1['value']
                                    },
                                    doc2_info={
                                        'id': doc2_id,
                                        'name': doc2_data['doc']['name'],
                                        'text': p2['context'],
                                        'value': p2['value']
                                    },
                                    severity=self._calculate_severity(p1, p2, pattern_type),
                                    confidence=min(p1['confidence'], p2['confidence']),
                                    entities_involved=list(set(p1.get('entities', []) + p2.get('entities', []))),
                                    context={
                                        'pattern_type': pattern_type,
                                        'context1': p1['context'],
                                        'context2': p2['context']
                                    },
                                    suggestion=self._generate_suggestion(p1, p2, pattern_type)
                                ))
        
        return contradictions
    
    def _extract_patterns(self, text: str) -> Dict[str, List[Dict]]:
        """Extract patterns from text"""
        patterns = {}
        
        for pattern_type, pattern_list in self.contradiction_patterns.items():
            patterns[pattern_type] = []
            
            for pattern_info in pattern_list:
                pattern = pattern_info['pattern']
                context = pattern_info['context']
                weight = pattern_info['weight']
                
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    # Get surrounding context
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    surrounding_context = text[start:end]
                    
                    patterns[pattern_type].append({
                        'value': match.group(1) if match.groups() else match.group(),
                        'context': surrounding_context,
                        'confidence': weight,
                        'pattern_type': context,
                        'position': match.span(),
                        'entities': [ent['text'] for ent in self.extract_entities(surrounding_context)]
                    })
        
        return patterns
    
    def _are_contradictory(self, p1: Dict, p2: Dict, pattern_type: str) -> bool:
        """Check if two patterns are contradictory"""
        val1, val2 = p1['value'].lower().strip(), p2['value'].lower().strip()
        
        if val1 == val2:
            return False
        
        if pattern_type == 'numerical':
            return self._check_numerical_contradiction(val1, val2)
        elif pattern_type == 'temporal':
            return self._check_temporal_contradiction(val1, val2)
        elif pattern_type == 'factual':
            return self._check_factual_contradiction(val1, val2)
        elif pattern_type == 'status':
            return self._check_status_contradiction(val1, val2)
        
        return False
    
    def _check_numerical_contradiction(self, val1: str, val2: str) -> bool:
        """Check for numerical contradictions"""
        try:
            # Extract numbers
            num1 = float(re.sub(r'[^\d.]', '', val1))
            num2 = float(re.sub(r'[^\d.]', '', val2))
            
            # Consider significant differences as contradictions
            if abs(num1 - num2) / max(num1, num2) > 0.1:  # 10% difference threshold
                return True
        except (ValueError, ZeroDivisionError):
            pass
        
        return False
    
    def _check_temporal_contradiction(self, val1: str, val2: str) -> bool:
        """Check for temporal contradictions"""
        # Simple temporal contradiction check
        temporal_opposites = [
            ('before', 'after'), ('early', 'late'), ('start', 'end'),
            ('beginning', 'end'), ('first', 'last'), ('soon', 'later')
        ]
        
        for word1, word2 in temporal_opposites:
            if (word1 in val1 and word2 in val2) or (word2 in val1 and word1 in val2):
                return True
        
        return False
    
    def _check_factual_contradiction(self, val1: str, val2: str) -> bool:
        """Check for factual contradictions"""
        factual_opposites = [
            ('is', 'is not'), ('can', 'cannot'), ('will', 'will not'),
            ('has', 'has not'), ('does', 'does not'), ('true', 'false'),
            ('yes', 'no'), ('correct', 'incorrect'), ('right', 'wrong')
        ]
        
        for word1, word2 in factual_opposites:
            if (word1 in val1 and word2 in val2) or (word2 in val1 and word1 in val2):
                return True
        
        return False
    
    def _check_status_contradiction(self, val1: str, val2: str) -> bool:
        """Check for status contradictions"""
        status_opposites = [
            ('completed', 'pending'), ('finished', 'in progress'),
            ('done', 'ongoing'), ('active', 'inactive'),
            ('approved', 'rejected'), ('success', 'failure')
        ]
        
        for word1, word2 in status_opposites:
            if (word1 in val1 and word2 in val2) or (word2 in val1 and word1 in val2):
                return True
        
        return False
    
    def _calculate_severity(self, p1: Dict, p2: Dict, pattern_type: str) -> str:
        """Calculate contradiction severity"""
        confidence = min(p1['confidence'], p2['confidence'])
        
        if pattern_type in ['numerical', 'temporal'] and confidence > 0.8:
            return 'Critical'
        elif confidence > 0.7:
            return 'High'
        elif confidence > 0.5:
            return 'Medium'
        else:
            return 'Low'
    
    def _generate_suggestion(self, p1: Dict, p2: Dict, pattern_type: str) -> str:
        """Generate suggestion for resolving contradiction"""
        suggestions = {
            'numerical': f"Verify which {pattern_type} value is correct: '{p1['value']}' or '{p2['value']}'",
            'temporal': f"Clarify the timeline - resolve conflicting dates/times between documents",
            'factual': f"Review factual statements for accuracy and consistency",
            'status': f"Update status information to ensure consistency across documents",
            'semantic': f"Review these statements for potential meaning conflicts"
        }
        
        return suggestions.get(pattern_type, "Review these conflicting statements for accuracy")
    
    def detect_contradictions(self, documents: List[Dict[str, Any]]) -> List[Contradiction]:
        """Main method to detect all types of contradictions"""
        if len(documents) < 2:
            return []
        
        contradictions = []
        
        # Detect pattern-based contradictions
        pattern_contradictions = self.detect_pattern_contradictions(documents)
        contradictions.extend(pattern_contradictions)
        
        # Detect semantic contradictions
        semantic_contradictions = self.detect_semantic_contradictions(documents)
        contradictions.extend(semantic_contradictions)
        
        # Remove duplicates and sort by confidence
        unique_contradictions = self._remove_duplicates(contradictions)
        unique_contradictions.sort(key=lambda x: x.confidence, reverse=True)
        
        return unique_contradictions
    
    def _remove_duplicates(self, contradictions: List[Contradiction]) -> List[Contradiction]:
        """Remove duplicate contradictions"""
        seen = set()
        unique = []
        
        for contradiction in contradictions:
            # Create a signature for the contradiction
            signature = (
                contradiction.type,
                contradiction.doc1_info['id'],
                contradiction.doc2_info['id'],
                contradiction.doc1_info.get('value', ''),
                contradiction.doc2_info.get('value', '')
            )
            
            if signature not in seen:
                seen.add(signature)
                unique.append(contradiction)
        
        return unique

# Enhanced function to integrate with your existing Streamlit app
def find_contradictions_enhanced(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enhanced contradiction detection function for Streamlit integration"""
    detector = EnhancedContradictionDetector()
    contradictions = detector.detect_contradictions(documents)
    
    # Convert to dictionary format compatible with existing Streamlit code
    contradiction_dicts = []
    for contradiction in contradictions:
        contradiction_dicts.append({
            'type': contradiction.type,
            'description': contradiction.description,
            'doc1_name': contradiction.doc1_info['name'],
            'doc1_value': contradiction.doc1_info.get('value', contradiction.doc1_info.get('text', '')),
            'doc2_name': contradiction.doc2_info['name'],
            'doc2_value': contradiction.doc2_info.get('value', contradiction.doc2_info.get('text', '')),
            'severity': contradiction.severity,
            'confidence': contradiction.confidence,
            'suggestion': contradiction.suggestion,
            'entities': contradiction.entities_involved,
            'context': contradiction.context
        })
    
    return contradiction_dicts

# The enhanced contradiction detection system is ready to use with your uploaded documents
# Simply call find_contradictions_enhanced(documents) where documents is a list of your uploaded document dictionaries