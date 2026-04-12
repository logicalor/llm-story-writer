"""Critique parser service for extracting scores and summaries from critic responses."""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from domain.exceptions import StoryGenerationError


@dataclass
class CritiqueScore:
    """Represents a score for a specific criterion."""
    criterion: str
    score: float
    max_score: float
    percentage: float
    notes: str


@dataclass
class CritiqueResult:
    """Represents the complete result of a critique."""
    critic_type: str
    scores: List[CritiqueScore]
    summary: str
    overall_score: float


class CritiqueParser:
    """Parser for extracting scores and summaries from critic responses."""
    
    def __init__(self):
        # Define the expected criteria and their max scores for each critic type
        self.critic_criteria = {
            "audiobook-producer": {
                "Pacing": 15,
                "Details": 15,
                "Flow": 15,
                "Genre": 10,
                "Consistency": 10,
                "Character Arc & Theme": 20,
                "Structure": 15
            },
            "book-club-moderator": {
                "Pacing": 15,
                "Details": 15,
                "Flow": 15,
                "Genre": 10,
                "Consistency": 10,
                "Character Arc & Theme": 20,
                "Structure": 15
            },
            "commercial-fiction-editor": {
                "Pacing": 15,
                "Details": 15,
                "Flow": 15,
                "Genre": 10,
                "Consistency": 10,
                "Character Arc & Theme": 20,
                "Structure": 15
            },
            "literary-fiction-reviewer": {
                "Pacing": 15,
                "Details": 15,
                "Flow": 15,
                "Genre": 10,
                "Consistency": 10,
                "Character Arc & Theme": 20,
                "Structure": 15
            },
            "publishing-acquisitions-editor": {
                "Pacing": 15,
                "Details": 15,
                "Flow": 15,
                "Genre": 10,
                "Consistency": 10,
                "Character Arc & Theme": 20,
                "Structure": 15
            },
            "subject-expert": {
                "Pacing": 15,
                "Details": 15,
                "Flow": 15,
                "Genre": 10,
                "Consistency": 10,
                "Character Arc & Theme": 20,
                "Structure": 15
            }
        }
    
    def parse_critique(self, critic_type: str, response: str) -> CritiqueResult:
        """Parse a critique response and extract scores and summary."""
        try:
            # Extract scores for each criterion
            scores = []
            criteria = self.critic_criteria.get(critic_type, {})
            
            for criterion, max_score in criteria.items():
                score_data = self._extract_criterion_score(response, criterion, max_score)
                if score_data:
                    scores.append(score_data)
            
            # Extract summary
            summary = self._extract_summary(response)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(scores)
            
            return CritiqueResult(
                critic_type=critic_type,
                scores=scores,
                summary=summary,
                overall_score=overall_score
            )
            
        except Exception as e:
            raise StoryGenerationError(f"Failed to parse critique from {critic_type}: {e}") from e
    
    def _extract_criterion_score(self, response: str, criterion: str, max_score: int) -> Optional[CritiqueScore]:
        """Extract score for a specific criterion."""
        # Look for the criterion section in the response
        # Pattern: "### Criterion (score/max_score)" followed by notes
        pattern = rf"### {re.escape(criterion)} \((\d+(?:\.\d+)?)/{max_score}\)\s*\n(.*?)(?=\n### |\n## |$)"
        
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if not match:
            # Try alternative pattern without the ###
            pattern = rf"{re.escape(criterion)} \((\d+(?:\.\d+)?)/{max_score}\)\s*\n(.*?)(?=\n### |\n## |$)"
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        
        if match:
            score = float(match.group(1))
            notes = match.group(2).strip()
            percentage = (score / max_score) * 100
            
            return CritiqueScore(
                criterion=criterion,
                score=score,
                max_score=max_score,
                percentage=percentage,
                notes=notes
            )
        
        return None
    
    def _extract_summary(self, response: str) -> str:
        """Extract the summary section from the critique response."""
        # Look for the summary section
        pattern = r"### Summary\s*\n(.*?)(?=\n### |\n## |$)"
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # If no summary section found, try to extract the last paragraph
        paragraphs = response.split('\n\n')
        if paragraphs:
            return paragraphs[-1].strip()
        
        return "No summary provided."
    
    def _calculate_overall_score(self, scores: List[CritiqueScore]) -> float:
        """Calculate the overall score based on all criterion scores."""
        if not scores:
            return 0.0
        
        # Since criteria scores add up to 100, just sum the raw scores
        total_score = sum(score.score for score in scores)
        
        return total_score
    
    def get_average_scores(self, critique_results: List[CritiqueResult]) -> Dict[str, float]:
        """Calculate average scores across all critics for each criterion."""
        if not critique_results:
            return {}
        
        # Group scores by criterion
        criterion_scores = {}
        for result in critique_results:
            for score in result.scores:
                if score.criterion not in criterion_scores:
                    criterion_scores[score.criterion] = []
                criterion_scores[score.criterion].append(score.percentage)
        
        # Calculate averages
        averages = {}
        for criterion, percentages in criterion_scores.items():
            averages[criterion] = sum(percentages) / len(percentages)
        
        return averages
    
    def get_overall_average_score(self, critique_results: List[CritiqueResult]) -> float:
        """Calculate the overall average score across all critics."""
        if not critique_results:
            return 0.0
        
        total_score = sum(result.overall_score for result in critique_results)
        return total_score / len(critique_results)
    
    def should_refine_outline(self, critique_results: List[CritiqueResult]) -> Tuple[bool, Dict[str, float], float]:
        """Determine if the outline should be refined based on critique scores."""
        if not critique_results:
            return True, {}, 0.0
        
        # Calculate average scores for each criterion
        average_scores = self.get_average_scores(critique_results)
        
        # Calculate overall average score
        overall_average = self.get_overall_average_score(critique_results)
        
        # Check if any criterion average is below 75%
        any_criterion_low = any(score < 75.0 for score in average_scores.values())
        
        # Check if overall average is below 85
        overall_low = overall_average < 85.0
        
        should_refine = any_criterion_low or overall_low
        
        return should_refine, average_scores, overall_average
    
    def format_critique_feedback(self, critique_results: List[CritiqueResult]) -> str:
        """Format all critique feedback into a single string for outline refinement."""
        feedback_parts = []
        
        for result in critique_results:
            feedback_parts.append(f"## {result.critic_type.replace('-', ' ').title()} Critique")
            feedback_parts.append(f"Overall Score: {result.overall_score:.1f}/100")
            feedback_parts.append("")
            
            for score in result.scores:
                feedback_parts.append(f"### {score.criterion}: {score.score}/{score.max_score} ({score.percentage:.1f}%)")
                feedback_parts.append(score.notes)
                feedback_parts.append("")
            
            feedback_parts.append(f"### Summary")
            feedback_parts.append(result.summary)
            feedback_parts.append("")
        
        return "\n".join(feedback_parts) 