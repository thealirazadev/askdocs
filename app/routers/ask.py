"""POST /ask - retrieve top-k chunks and compose a cited answer."""

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.deps import get_metadata_store, get_vector_store, require_api_key
from app.schemas.ask import AskRequest, AskResponse, Citation
from app.services.answering import answer_question
from app.services.claude_client import ClaudeClient
from app.services.metadata import MetadataStore
from app.services.vectorstore import VectorStore

router = APIRouter(dependencies=[Depends(require_api_key)])


def get_claude_client(settings: Settings = Depends(get_settings)) -> ClaudeClient:
    return ClaudeClient(api_key=settings.anthropic_api_key, model=settings.claude_model)


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    settings: Settings = Depends(get_settings),
    metadata_store: MetadataStore = Depends(get_metadata_store),
    vector_store: VectorStore = Depends(get_vector_store),
    claude_client: ClaudeClient = Depends(get_claude_client),
) -> AskResponse:
    top_k = body.top_k or settings.top_k
    result = answer_question(body.question, top_k, vector_store, metadata_store, claude_client)
    return AskResponse(
        answer=result.answer,
        citations=[Citation(**vars(c)) for c in result.citations],
    )
