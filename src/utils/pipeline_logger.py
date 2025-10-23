"""
Pipeline logger for tracking the design research agent's orchestration flow.
Provides structured, readable logging of each pipeline stage.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime


class PipelineLogger:
    """Logs each stage of the orchestration pipeline with clear formatting."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.stage_counter = 0
        self._print_pipeline_overview()
    
    def _separator(self, char: str = "=", length: int = 80) -> str:
        return char * length
    
    def _print(self, content: str) -> None:
        if self.enabled:
            print(content)
    
    def _print_pipeline_overview(self) -> None:
        """Print a visual overview of the pipeline at initialization."""
        if not self.enabled:
            return
        
        overview = """
╔════════════════════════════════════════════════════════════════════════════════╗
║                        DESIGN RESEARCH AGENT PIPELINE                          ║
╚════════════════════════════════════════════════════════════════════════════════╝

  User Query
      ↓
  Query Enhancement (classify + generate variants)
      ↓
  Multi-Source Search (Exa + optional Brave)
      ↓
  Heuristic Filter & Dedup (remove duplicates, rank by authority)
      ↓
  Fetch & Extract (content + images via Jina)
      ↓
  LLM Synthesis (generate structured JSON)
      ↓
  Pydantic Validation (enforce schema)
      ↓
  Structured Output

────────────────────────────────────────────────────────────────────────────────
"""
        self._print(overview)
    
    def log_stage(self, stage_name: str, data: Dict[str, Any]) -> None:
        """Log a pipeline stage with structured data."""
        if not self.enabled:
            return
        
        self.stage_counter += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self._print(f"\n{self._separator()}")
        self._print(f"STAGE {self.stage_counter}: {stage_name.upper()}")
        self._print(f"Time: {timestamp}")
        self._print(self._separator("-"))
        
        for key, value in data.items():
            self._print(f"\n{key}:")
            self._format_value(value, indent=2)
        
        self._print(f"\n{self._separator()}\n")
    
    def _format_value(self, value: Any, indent: int = 0) -> None:
        """Format and print a value with proper indentation."""
        prefix = " " * indent
        
        if isinstance(value, str):
            # Truncate very long strings
            if len(value) > 500:
                self._print(f"{prefix}{value[:500]}...")
                self._print(f"{prefix}[TRUNCATED - Total length: {len(value)} chars]")
            else:
                self._print(f"{prefix}{value}")
        
        elif isinstance(value, (list, tuple)):
            if not value:
                self._print(f"{prefix}[]")
            else:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._print(f"{prefix}[{i}]:")
                        self._format_dict(item, indent + 2)
                    else:
                        self._print(f"{prefix}[{i}] {item}")
        
        elif isinstance(value, dict):
            self._format_dict(value, indent)
        
        elif isinstance(value, (int, float, bool, type(None))):
            self._print(f"{prefix}{value}")
        
        else:
            self._print(f"{prefix}{str(value)}")
    
    def _format_dict(self, data: Dict, indent: int = 0) -> None:
        """Format a dictionary with proper indentation."""
        prefix = " " * indent
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                self._print(f"{prefix}{k}:")
                self._format_value(v, indent + 2)
            else:
                # Truncate long values
                str_v = str(v)
                if len(str_v) > 200:
                    str_v = str_v[:200] + "..."
                self._print(f"{prefix}{k}: {str_v}")
    
    def log_user_query(self, question: str, max_results: int, include_images: bool) -> None:
        """Log the initial user query."""
        self.log_stage("User Query", {
            "Question": question,
            "Max Results": max_results,
            "Include Images": include_images
        })
    
    def log_query_enhancement(self, classification: str, variants: List[str]) -> None:
        """Log query enhancement results."""
        self.log_stage("Query Enhancement", {
            "Classification": classification,
            "Search Variants Generated": variants,
            "Total Variants": len(variants)
        })
    
    def log_search_results(
        self, 
        exa_results: int, 
        brave_results: int, 
        total_before_dedup: int,
        sample_urls: List[str]
    ) -> None:
        """Log search results from all providers."""
        self.log_stage("Multi-Source Search", {
            "Exa Results": exa_results,
            "Brave Results": brave_results,
            "Total Before Dedup": total_before_dedup,
            "Sample URLs (first 5)": sample_urls[:5]
        })
    
    def log_dedup_and_rank(
        self, 
        before_count: int, 
        after_count: int,
        ranked_results: List[Dict]
    ) -> None:
        """Log deduplication and ranking results."""
        # Extract simplified info from ranked results
        simplified = [
            {
                "title": r.get("title", "N/A")[:60],
                "url": r.get("url", "N/A"),
                "score": r.get("score", "N/A")
            }
            for r in ranked_results[:10]  # Show top 10
        ]
        
        self.log_stage("Heuristic Filter and Dedup", {
            "Before Dedup": before_count,
            "After Dedup & Ranking": after_count,
            "Top Ranked Results": simplified
        })
    
    def log_extraction(self, extracted: List[Dict]) -> None:
        """Log content extraction results."""
        simplified = []
        meta_count = 0
        dom_count = 0
        none_count = 0
        dims_present_count = 0
        dims_missing_count = 0

        for e in extracted[:5]:  # Show first 5
            content_preview = e.get("content", "")
            if content_preview:
                content_preview = content_preview[:200] + "..." if len(content_preview) > 200 else content_preview
            
            source = e.get("image_source")  # meta | dom | none
            if source == "meta":
                meta_count += 1
            elif source == "dom":
                dom_count += 1
            else:
                none_count += 1

            dims = e.get("image_dims") or (None, None)
            if any(d is not None for d in dims):
                dims_present_count += 1
            else:
                dims_missing_count += 1

            simplified.append({
                "title": e.get("title", "N/A")[:60],
                "url": e.get("url", "N/A"),
                "content_length": len(e.get("content", "")),
                "content_preview": content_preview,
                "has_image": bool(e.get("image_url"))
            })
        
        self.log_stage("Fetch and Extract", {
            "Total Extracted": len(extracted),
            "Extraction Details (first 5)": simplified,
            "Image Sources": {
                "meta": meta_count,
                "dom": dom_count,
                "none": none_count,
            },
            "Image Dimensions": {
                "with_dims": dims_present_count,
                "without_dims": dims_missing_count,
            }
        })
    
    def log_llm_synthesis(
        self, 
        prompt_preview: str,
        prompt_length: int,
        raw_response: str,
        llm_provider: str,
    ) -> None:
        """Log LLM synthesis input and output (preview only)."""
        payload: Dict[str, Any] = {
            "LLM Provider": llm_provider,
            "Prompt Length (chars)": prompt_length,
            "Prompt Preview (first 500 chars)": prompt_preview[:500],
            "Raw LLM Response": raw_response,
            "Response Length (chars)": len(raw_response),
        }
        self.log_stage("LLM Synthesis to JSON", payload)
    
    def log_validation(self, success: bool, response_summary: Optional[Dict] = None) -> None:
        """Log Pydantic validation results."""
        data = {"Validation Success": success}
        
        if success and response_summary:
            data.update({
                "Response Summary": {
                    "Classification": response_summary.get("classification"),
                    "Summary Length": len(response_summary.get("summary", "")),
                    "Best Practices Count": response_summary.get("best_practices_count"),
                    "Examples Count": response_summary.get("examples_count"),
                    "Sources Count": response_summary.get("sources_count"),
                    "Has Considerations": response_summary.get("has_considerations")
                }
            })
        
        self.log_stage("Pydantic Validation", data)
    
    def log_completion(self, total_time_seconds: float) -> None:
        """Log pipeline completion."""
        self.log_stage("Pipeline Complete", {
            "Total Time": f"{total_time_seconds:.2f} seconds",
            "Status": "SUCCESS"
        })


# Global instance for easy access
_logger_instance: Optional[PipelineLogger] = None


def get_logger(enabled: bool = True) -> PipelineLogger:
    """Get or create the global pipeline logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = PipelineLogger(enabled=enabled)
    return _logger_instance


def reset_logger() -> None:
    """Reset the global logger instance."""
    global _logger_instance
    _logger_instance = None

