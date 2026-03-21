"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import re
from typing import List

from backend.data.literature_sources import PaperObject

def _clean_authors(raw_authors: str) -> str:
    """removes html tags and handles 'et al' conversions for bibtex 'and' syntax lol"""
                # Strip HTML
    clean = re.sub('<[^<]+?>', '', raw_authors)
    
        
        
        
    # Handle implicit et al.
    if "et al." in clean or "etal" in clean:
        clean = clean.replace("et al.", "").replace("etal", "").strip()
        names = [n.strip() for n in clean.split(",") if n.strip()]
        if names:
            return " and ".join(names) + " and others"
        return "Unknown and others"
        
    names = [n.strip() for n in clean.split(",") if n.strip()]
    if len(names) > 5:
        return " and ".join(names[:5]) + " and others"
    elif len(names) > 0:
        return " and ".join(names)
        
    return clean if clean else "Unknown Author"

def _clean_bibtex_value(val: str) -> str:
    """escapes problematic characters for bibtex compilation lol"""
    v = str(val).replace("&", "\\&").replace("%", "\\%").replace("$", "\\$")
    v = v.replace("#", "\\#").replace("_", "\\_").replace("{", "\\{").replace("}", "\\}")
    return v

def build_bibtex_entries(papers: List[PaperObject]) -> str:
    """Generates a complete BibTeX formatted string for a collection of papers.
    
    Args:
        papers: List of extracted PaperObjects from Agent 2.
        
    Returns:
        A multiline string formatted as a valid .bib file.
    """
    entries = []
    
    for idx, paper in enumerate(papers):
                                # Generate a safe citation key (first author surname + year)
        authors = _clean_authors(paper.authors)
        first_author = authors.split(" and ")[0].split()[-1] if authors != "Unknown Author" else "Anon"
        c_key = "".join(filter(str.isalnum, first_author)) + str(paper.year) + str(idx)
        
                
                
                
        # Determine entry type
        repo = _clean_bibtex_value(paper.journal_or_repo.lower())
        title = _clean_bibtex_value(paper.title)
        
        if "arxiv" in repo or "ssrn" in repo or "preprint" in repo:
                                                # Preprints use @misc
            entry = [
                f"@misc{{{c_key},",
                f"  title = {{{title}}},",
                f"  author = {{{authors}}},",
                f"  year = {{{paper.year}}},",
                f"  howpublished = {{{_clean_bibtex_value(paper.journal_or_repo)}}},"
            ]
        else:
                                                # Published papers use @article
            entry = [
                f"@article{{{c_key},",
                f"  title = {{{title}}},",
                f"  author = {{{authors}}},",
                f"  year = {{{paper.year}}},",
                f"  journal = {{{_clean_bibtex_value(paper.journal_or_repo)}}},"
            ]
            
        if paper.url:
            entry.append(f"  url = {{{_clean_bibtex_value(paper.url)}}},")
            
                    
                    
                    
        # Add summary finding as a note for the context Appendix
        note_str = paper.key_finding.replace("\n", " ") if paper.key_finding else ""
        if note_str:
            entry.append(f"  note = {{{_clean_bibtex_value(note_str[:250])}}},")
            
        entry.append("}")
        entries.append("\n".join(entry))
        
    return "\n\n".join(entries)
