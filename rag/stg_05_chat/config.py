from dataclasses import dataclass


@dataclass
class ChatConfig:
    persona:              str   = ""   # e.g. "You are an Acme assistant, a project management platform"
    history_limit:        int   = 20     # max turns kept in memory
    min_rerank_score:     float = 0.5    # chunks below this score are excluded from context
    min_retrieval_score:  float = 0.40   # if best candidate is below this, skip RAG entirely
    stream:               bool  = False   # stream answer tokens as they arrive
    use_tools:            bool  = True
    rewrite_query:        bool  = True    # expand query before retrieval for better embedding matches
