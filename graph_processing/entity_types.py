"""
Entity and relationship types for Machine Learning/Deep Learning domain.
"""

from enum import Enum


class EntityType(str, Enum):
    """Entity types specific to ML/DL domain."""

    # Core ML Concepts
    ALGORITHM = "ALGORITHM"              # Neural networks, gradient descent, etc.
    MODEL = "MODEL"                      # ResNet, BERT, GPT, etc.
    ARCHITECTURE = "ARCHITECTURE"        # Transformer, CNN, RNN, etc.
    TECHNIQUE = "TECHNIQUE"              # Regularization, normalization, etc.
    CONCEPT = "CONCEPT"                  # Overfitting, bias-variance, etc.

    # Model Components
    LAYER = "LAYER"                      # Conv layer, attention layer, etc.
    ACTIVATION = "ACTIVATION"            # ReLU, Sigmoid, etc.
    LOSS_FUNCTION = "LOSS_FUNCTION"      # Cross-entropy, MSE, etc.
    OPTIMIZER = "OPTIMIZER"              # Adam, SGD, RMSprop, etc.

    # Data Related
    DATASET = "DATASET"                  # ImageNet, COCO, etc.
    DATA_TYPE = "DATA_TYPE"              # Image, text, audio, etc.
    PREPROCESSING = "PREPROCESSING"      # Normalization, augmentation, etc.
    FEATURE = "FEATURE"                  # Image features, text embeddings, etc.

    # Performance & Metrics
    METRIC = "METRIC"                    # Accuracy, F1-score, BLEU, etc.
    BENCHMARK = "BENCHMARK"              # Performance benchmarks
    EVALUATION = "EVALUATION"            # Evaluation methods

    # Tasks & Applications
    TASK = "TASK"                        # Classification, detection, etc.
    APPLICATION = "APPLICATION"          # Computer vision, NLP, etc.
    DOMAIN = "DOMAIN"                    # Healthcare AI, autonomous driving, etc.

    # Frameworks & Tools
    FRAMEWORK = "FRAMEWORK"              # PyTorch, TensorFlow, etc.
    LIBRARY = "LIBRARY"                  # NumPy, scikit-learn, etc.
    TOOL = "TOOL"                        # Jupyter, MLflow, etc.

    # Research & Theory
    PAPER = "PAPER"                      # Research papers
    RESEARCHER = "RESEARCHER"            # Authors, contributors
    ORGANIZATION = "ORGANIZATION"        # Research labs, companies
    THEORY = "THEORY"                    # Theoretical concepts

    # Training & Deployment
    HYPERPARAMETER = "HYPERPARAMETER"    # Learning rate, batch size, etc.
    TRAINING_METHOD = "TRAINING_METHOD"  # Transfer learning, fine-tuning, etc.
    HARDWARE = "HARDWARE"                # GPU, TPU, etc.
    DEPLOYMENT = "DEPLOYMENT"            # Edge deployment, cloud, etc.

    # Other
    CHALLENGE = "CHALLENGE"              # Problems to solve
    LIMITATION = "LIMITATION"            # Known limitations
    GENERAL = "GENERAL"                  # General entities


class RelationshipType(str, Enum):
    """Relationship types for ML/DL knowledge graph."""

    # Hierarchical relationships
    IS_A = "IS_A"                        # ResNet IS_A CNN architecture
    PART_OF = "PART_OF"                  # Attention layer PART_OF Transformer
    SUBTYPE_OF = "SUBTYPE_OF"           # BERT SUBTYPE_OF Transformer
    EXTENDS = "EXTENDS"                  # GPT-3 EXTENDS GPT-2

    # Usage relationships
    USES = "USES"                        # Model USES optimizer
    REQUIRES = "REQUIRES"                # Training REQUIRES dataset
    APPLIES_TO = "APPLIES_TO"           # Technique APPLIES_TO task
    IMPLEMENTS = "IMPLEMENTS"            # Code IMPLEMENTS algorithm

    # Performance relationships
    IMPROVES = "IMPROVES"                # Technique IMPROVES metric
    OUTPERFORMS = "OUTPERFORMS"         # Model A OUTPERFORMS Model B
    EVALUATED_ON = "EVALUATED_ON"        # Model EVALUATED_ON benchmark
    ACHIEVES = "ACHIEVES"                # Model ACHIEVES metric score

    # Development relationships
    TRAINED_ON = "TRAINED_ON"            # Model TRAINED_ON dataset
    OPTIMIZED_BY = "OPTIMIZED_BY"       # Training OPTIMIZED_BY optimizer
    DEVELOPED_BY = "DEVELOPED_BY"        # Model DEVELOPED_BY organization
    PUBLISHED_IN = "PUBLISHED_IN"        # Research PUBLISHED_IN paper

    # Problem-solution relationships
    SOLVES = "SOLVES"                    # Algorithm SOLVES problem
    ADDRESSES = "ADDRESSES"              # Technique ADDRESSES challenge
    MITIGATES = "MITIGATES"             # Method MITIGATES limitation

    # Similarity & comparison
    SIMILAR_TO = "SIMILAR_TO"            # Concept A SIMILAR_TO Concept B
    ALTERNATIVE_TO = "ALTERNATIVE_TO"    # Method A ALTERNATIVE_TO Method B
    COMPETES_WITH = "COMPETES_WITH"     # Model A COMPETES_WITH Model B

    # Dependency relationships
    DEPENDS_ON = "DEPENDS_ON"            # Feature DEPENDS_ON preprocessing
    ENABLES = "ENABLES"                  # Hardware ENABLES training
    BASED_ON = "BASED_ON"                # Work BASED_ON prior research

    # Temporal relationships
    PRECEDES = "PRECEDES"                # Paper A PRECEDES Paper B
    SUCCEEDS = "SUCCEEDS"                # Version 2 SUCCEEDS Version 1
    INSPIRED_BY = "INSPIRED_BY"         # Work INSPIRED_BY prior work

    # Application relationships
    APPLIED_IN = "APPLIED_IN"            # Model APPLIED_IN domain
    SUITABLE_FOR = "SUITABLE_FOR"        # Architecture SUITABLE_FOR task

    # General relationships
    RELATED_TO = "RELATED_TO"            # Generic relationship
    MENTIONED_WITH = "MENTIONED_WITH"    # Co-occurrence in text


# Entity type descriptions for LLM extraction
ENTITY_TYPE_DESCRIPTIONS = {
    EntityType.ALGORITHM: "A computational procedure or formula (e.g., backpropagation, gradient descent)",
    EntityType.MODEL: "A specific ML/DL model instance (e.g., BERT, GPT-3, ResNet-50)",
    EntityType.ARCHITECTURE: "A model structure or design pattern (e.g., Transformer, CNN, LSTM)",
    EntityType.TECHNIQUE: "A method or approach (e.g., dropout, batch normalization, data augmentation)",
    EntityType.DATASET: "A collection of data used for training/evaluation (e.g., ImageNet, MNIST)",
    EntityType.METRIC: "A performance measurement (e.g., accuracy, F1-score, perplexity)",
    EntityType.TASK: "An ML problem type (e.g., image classification, object detection, machine translation)",
    EntityType.FRAMEWORK: "A software framework (e.g., PyTorch, TensorFlow, JAX)",
}

# Relationship type descriptions for LLM extraction
RELATIONSHIP_TYPE_DESCRIPTIONS = {
    RelationshipType.IS_A: "Entity is a type/instance of another (hierarchical)",
    RelationshipType.USES: "Entity uses or employs another entity",
    RelationshipType.IMPROVES: "Entity improves or enhances another",
    RelationshipType.TRAINED_ON: "Model is trained on a dataset",
    RelationshipType.EVALUATED_ON: "Model is evaluated on a benchmark/dataset",
    RelationshipType.OUTPERFORMS: "Entity performs better than another",
    RelationshipType.PART_OF: "Entity is a component of another",
    RelationshipType.BASED_ON: "Entity is built upon or derived from another",
}
