"""Parallel content extraction to speed up fetching from multiple URLs."""

from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.extract.jina_extractor import fetch_with_jina
from src.extract.image_extractor import extract_primary_image_debug


def extract_content_parallel(
    ranked_results: List[Dict],
    include_images: bool = True,
    max_workers: int = 5
) -> List[Dict]:
    """
    Extract content from multiple URLs in parallel using threads.
    
    Args:
        ranked_results: List of ranked search results with 'url' and 'title'
        include_images: Whether to extract images
        max_workers: Maximum number of parallel workers
    
    Returns:
        List of dicts with title, url, content, and optional image_url
    """
    extracted = []
    
    def fetch_single(result: Dict) -> Dict:
        """Fetch content and image for a single URL."""
        url = result["url"]
        title = result.get("title")
        
        try:
            content = fetch_with_jina(url).get("content", "")
        except Exception as e:
            print(f"Warning: Failed to fetch {url}: {e}")
            content = ""
        
        image_url = None
        source_type = "none"
        dims = (None, None)
        if include_images:
            try:
                image_url, source_type, dims = extract_primary_image_debug(url)
            except Exception as e:
                print(f"Warning: Failed to extract image from {url}: {e}")
        
        return {
            "title": title,
            "url": url,
            "content": content,
            "image_url": image_url,
            "image_source": source_type,
            "image_dims": dims,
        }
    
    # Use ThreadPoolExecutor for parallel I/O-bound operations
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_result = {
            executor.submit(fetch_single, result): result
            for result in ranked_results
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_result):
            try:
                extracted_item = future.result()
                extracted.append(extracted_item)
            except Exception as e:
                result = future_to_result[future]
                print(f"Error processing {result.get('url')}: {e}")
    
    # Preserve original order by sorting based on ranked_results
    url_to_index = {r["url"]: i for i, r in enumerate(ranked_results)}
    extracted.sort(key=lambda x: url_to_index.get(x["url"], 999))
    
    return extracted

