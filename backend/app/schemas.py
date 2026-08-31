from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


SessionStatus = Literal[
    "new",
    "diagnose",
    "plan",
    "explain",
    "visualize",
    "practice",
    "evaluate",
    "adapt",
    "completed",
]


class StudentProfile(BaseModel):
    name: str = "Student"
    current_level: str = "beginner"
    self_description: str = ""
    goals: List[str] = Field(default_factory=lambda: ["Learn CS fundamentals"])
    known_concepts: List[str] = Field(default_factory=list)
    difficult_concepts: List[str] = Field(default_factory=list)
    time_budget_minutes: int = 30


class VisualizationEntity(BaseModel):
    id: str
    kind: str
    label: str
    rows: Optional[List[str]] = None
    value: Optional[Any] = None


# ── Scene script: a per-topic animated scene the frontend CSS engine performs ──

SceneActorKind = Literal[
    "box", "token", "node", "sun", "drop", "bubble", "arrow", "counter",
    "chip", "meter", "lane", "creature", "stack",
]

SceneRenderer = Literal[
    "emoji-scene", "graph", "diagram", "image-overlay", "flow", "comparison",
]

SceneAction = Literal[
    "appear", "disappear", "move", "pulse", "shake", "split", "merge",
    "fill", "increment", "highlight", "dim", "connect", "emit",
    "draw_curve", "shift_curve", "draw_point", "move_point", "highlight_point", "add_annotation",
]


class SceneActor(BaseModel):
    id: str
    kind: SceneActorKind
    label: str
    icon: str = ""
    # Position on a 0-100 percentage grid (top-left origin)
    x: float = 50
    y: float = 50
    color: str = ""
    value: Optional[Any] = None


class SceneEffect(BaseModel):
    actor: str
    action: SceneAction
    to_x: Optional[float] = None
    to_y: Optional[float] = None
    label: Optional[str] = None
    value: Optional[Any] = None
    # For split/merge/emit: id of the actor created (or partner actor)
    target: Optional[str] = None


class SceneStep(BaseModel):
    id: str
    # One short sentence shown as the step headline (max ~110 chars)
    caption: str
    # 1-2 sentences explaining WHY this happens / what it proves (shown under the caption)
    narration: str = ""
    effects: List[SceneEffect] = Field(default_factory=list)


class SceneScript(BaseModel):
    background: str = "default"
    renderer: SceneRenderer = "emoji-scene"
    # One sentence: what problem/question is this animation answering?
    problem: str = ""
    # One sentence: what should the student watch for / what does success look like?
    goal: str = ""
    # One sentence: the conclusion the student should walk away with (the answer/result).
    takeaway: str = ""
    actors: List[SceneActor] = Field(default_factory=list)
    steps: List[SceneStep] = Field(default_factory=list)
    graph_data: Optional[Dict[str, Any]] = None


class VisualizationRelation(BaseModel):
    from_: str = Field(alias="from")
    to: str
    label: str

    model_config = {"populate_by_name": True}


class VisualizationState(BaseModel):
    id: str
    labels: List[str] = Field(default_factory=list)
    highlight: List[str] = Field(default_factory=list)


class VisualizationTransition(BaseModel):
    from_: str = Field(alias="from")
    to: str
    animation: str
    durationMs: int = 900

    model_config = {"populate_by_name": True}


class VisualizationQuestion(BaseModel):
    id: str
    prompt: str
    expectedObservations: List[str] = Field(default_factory=list)


class VisualizationSpec(BaseModel):
    type: Literal["flow", "array", "comparison", "node", "metric", "question", "stack", "linked-list", "process", "timeline"]
    id: str
    title: str
    layout: Dict[str, str] = Field(default_factory=lambda: {"orientation": "left-right"})
    entities: List[VisualizationEntity] = Field(default_factory=list)
    relations: List[VisualizationRelation] = Field(default_factory=list)
    states: List[VisualizationState] = Field(default_factory=list)
    transitions: List[VisualizationTransition] = Field(default_factory=list)
    questions: List[VisualizationQuestion] = Field(default_factory=list)
    expectedObservations: List[str] = Field(default_factory=list)
    renderer: SceneRenderer = "emoji-scene"
    # Rich per-topic animated scene (interpreted by the frontend scene engine).
    scene: Optional[SceneScript] = None


class VisualizationClassifier(BaseModel):
    renderer: SceneRenderer = "emoji-scene"
    reasoning: str = ""


class DiagnosticReport(BaseModel):
    understanding: List[str]
    missing_prerequisites: List[str]
    misconceptions: List[str]
    confidence: float
    summary: str


class LearningPlan(BaseModel):
    goal: str
    target_concept: str
    steps: List[str]
    time_budget_minutes: int
    rationale: str


class MethodModel(BaseModel):
    id: str
    name: str
    explanation: str
    complexity: Dict[str, str]
    code: str
    visualization_spec_ref: str


class ConceptModel(BaseModel):
    concept_id: str
    title: str
    canonical_definition: str
    key_facts: List[str]
    prerequisites: List[str]
    misconceptions: List[str]
    explanation_summary: str
    teaching_emphasis: List[str]
    methods: List[MethodModel] = Field(default_factory=list)
    narrative_intuition: str = ""
    deep_mechanism: str = ""
    real_world_scenario: str = ""
    common_pitfalls: List[str] = Field(default_factory=list)


class ExerciseTask(BaseModel):
    id: str
    type: str
    prompt: str
    expected_reasoning: str
    hints: List[str] = Field(default_factory=list)


class ExerciseSet(BaseModel):
    exercises: List[ExerciseTask]
    summary: str


class EvaluationResult(BaseModel):
    passed: bool
    score: float
    reasoning_quality: str
    misconception_detected: List[str]
    feedback: str


class AdaptationDecision(BaseModel):
    action: str
    reason: str
    next_step: SessionStatus
    updated_difficulty: str


class ConceptNode(BaseModel):
    concept_id: str
    title: str
    domain: str = "CS"
    subdomain: str = "Software/DSA"
    prerequisites: List[str] = Field(default_factory=list)
    canonical_definition: str
    misconceptions: List[str] = Field(default_factory=list)
    explanation_depths: List[str] = Field(default_factory=list)
    representation_types: List[str] = Field(default_factory=list)
    evaluation_modes: List[str] = Field(default_factory=list)


class QuizQuestion(BaseModel):
    """One multiple-choice warm-up question used to place the student before teaching."""
    question: str
    options: List[str]
    correct_index: int
    misconception_tag: str = ""
    explanation: str = ""


class TopicBlueprint(BaseModel):
    """Synthesized curriculum node for a free-text topic request (any domain)."""
    concept_id: str
    title: str
    domain: str = "Custom"
    subdomain: str = "Learner Requested"
    canonical_definition: str
    key_facts: List[str] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    explanation_depths: List[str] = Field(default_factory=list)
    # Narrative depth fields for comprehensive conceptual understanding
    narrative_intuition: str = ""
    deep_mechanism: str = ""
    real_world_scenario: str = ""
    common_pitfalls: List[str] = Field(default_factory=list)
    # One-line summary shown in the visualizer input bar (e.g. "array = [4, -2, 7], target = 5")
    input_display: str = ""
    # 3-6 concrete tokens the animated boxes step through (e.g. ["seed", "sprout", "leaf"])
    example_values: List[str] = Field(default_factory=list)
    # A concrete worked example the visualization spec must be grounded in
    example_walkthrough: str = ""
    # Practice prompt the student answers after the visualizer
    practice_challenge: str = ""
    # 3 multiple-choice warm-up questions probing prerequisites/misconceptions
    diagnostic_quiz: List[QuizQuestion] = Field(default_factory=list)


class ChatAskRequest(BaseModel):
    session_id: str
    user_question: str
    current_screen: str = "general"


class ChatAskResponse(BaseModel):
    reply: str
    suggested_followups: List[str] = Field(default_factory=list)


class DomainAdapter(BaseModel):
    domain_id: str
    subdomain_id: str
    concept_graph: List[ConceptNode] = Field(default_factory=list)
    misconceptions: Dict[str, List[str]] = Field(default_factory=dict)
    explanation_templates: Dict[str, str] = Field(default_factory=dict)
    visualization_templates: Dict[str, str] = Field(default_factory=dict)
    practice_templates: Dict[str, str] = Field(default_factory=dict)
    evaluation_rules: Dict[str, Any] = Field(default_factory=dict)


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    username: str


class StudentSession(BaseModel):
    session_id: str
    student_profile: StudentProfile
    username: Optional[str] = None
    current_domain: str = "CS"
    current_subdomain: str = "Software/DSA"
    active_topic: str = "Two Sum — HashMap lookup vs brute force"
    session_status: SessionStatus = "new"
    diagnosis: Optional[DiagnosticReport] = None
    learning_plan: Optional[LearningPlan] = None
    concept_history: List[ConceptModel] = Field(default_factory=list)
    practice_history: List[ExerciseSet] = Field(default_factory=list)
    adaptation_log: List[AdaptationDecision] = Field(default_factory=list)
    # Checkpoint answers from visualization questions: [{question_id, answer}]
    student_answers: List[Dict[str, str]] = Field(default_factory=list)
    session_progress: Dict[str, Any] = Field(default_factory=lambda: {
        "completed_steps": [],
        "revisit_queue": [],
        "mastery_trend": [],
        "next_best_action": "diagnose"
    })
    interaction_state: Dict[str, Any] = Field(default_factory=lambda: {
        "current_visualization": None,
        "current_question": None,
        "current_feedback": ""
    })
    metadata: Dict[str, Any] = Field(default_factory=lambda: {
        "created_at": "",
        "updated_at": "",
        "agent_trace": []
    })


class SessionStartRequest(BaseModel):
    student_profile: Optional[StudentProfile] = None
    concept_id: Optional[str] = None
    # Free-text topic request: when provided, the platform synthesizes a custom
    # curriculum node for ANY topic instead of using a pre-built concept_id.
    topic_request: Optional[str] = None


class SessionAdvanceRequest(BaseModel):
    session_id: str
    answer: Optional[str] = None


class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str

