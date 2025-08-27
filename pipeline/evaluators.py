from typing import List

import pandas as pd
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from models.schemas import CriticalThinkingAssessment, CriticalThinkingStandard, PipelineConfig
from utils.errors import APIError
from utils.logging import get_logger

logger = get_logger(__name__)


class StandardResponse(BaseModel):
    """Response model for critical thinking standard evaluation"""

    name: str = Field(description="Name of the standard")
    evaluation: str = Field(description="Evaluation of the standard")
    rating: int = Field(description="Rating of the standard - 0-10")
    followup_questions: List[str] = Field(description="Followup questions for the standard")


class EvaluationResponse(BaseModel):
    """Complete evaluation response model"""

    standards: List[StandardResponse]


class CriticalThinkingEvaluator:
    """Critical thinking standards evaluator using Google GenAI"""

    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

        self.evaluation_prompt_template = """
# CT : Assess standards 

Given text below, please assess the contents against the critical thinking standards defined below. based on the standard in depth guidelines, use the questions in order to view the given text in perspective of standards and given goal. 

My goal is to help people resolve their problems being able to empathise understand and move quickly. 

Finally, for the output format, 
- for each standard please provide a follow up questions. As "Those" questions is crucial needed to address a further standard alignment, in order to capture the higher standard of information, or inference assumed in the text. 


Here are the standards in depth : 

## Standards in depth : Clarity

Clarity is fundamental; without it, the accuracy or relevance of a statement can't be assessed. Questions like "Could you elaborate?" or "Could you give an example?" help clarify statements, making them understandable and actionable. For instance, transforming a vague question about the American education system into a specific inquiry about educators' roles in skill development clarifies the issue and facilitates effective discussion and solutions.

When engaging in discussions, it's crucial to clarify vague statements to understand their true implications. For instance, the claim "welfare is corrupt" can imply various issues ranging from moral concerns about the distribution of goods to legal loopholes and ethical problems with recipients. Such statements require examination to determine their clarity and accuracy. 

- Could you elaborate? 
- Could you illustrate what you mean? 
- Could you give me an example?

## Standards in depth : Accuracy

Critical thinking involves a systematic approach to evaluating the accuracy and clarity of statements and beliefs. It requires questioning the truthfulness and precision of what is heard or read, especially when skepticism is warranted. Often, statements are presented in a way that does not align with reality, either due to intentional misrepresentation, such as in advertising, or biased perspectives that favor one's own beliefs while dismissing others'. For instance, an advertisement claiming "100% pure water" that contains trace chemicals is inaccurate. Similarly, personal biases can lead us to accept statements that align with our beliefs without scrutiny and reject opposing views. Good critical thinkers challenge their own views and others', striving for a clear and accurate understanding of issues, regardless of personal biases or external influences. This skill is crucial in differentiating between what is clear and what might be misleading or vague, thereby enhancing one's ability to address and reformulate problems more effectively.

- How could we check on that? 
- How could we find out if that is true? 
- How could we verify or test that?

## Standards in depth : Precision

Precision in communication is crucial for clarity and effective understanding, especially in situations where specifics are essential to make informed decisions or solve problems. 
For instance, a vague statement like "Jack is overweight" lacks the necessary detail to understand the severity of the situation—it could mean an excess of 1 pound or 500 pounds. 
In everyday interactions, such as confirming the presence of milk in the refrigerator, a simple "Yes" might suffice. However, in more complex scenarios like financial advice or medical instructions, precise information is vital. 

Asking probing questions to understand the specifics can lead to better outcomes and prevent misunderstandings. For example, unclear directions to a location can result in getting lost, highlighting the negative consequences of imprecise communication. Thus, recognizing when and where precision is needed can significantly enhance the effectiveness of our interactions.

- Could you be more specific? 
- Could you give me more details? 
- Could you be more exact?

## Standards in depth : Depth

When tackling complex issues, it's essential to delve beyond superficial solutions to understand and address the underlying complexities. Simply responding to intricate problems with clear, accurate, and relevant answers, like the "Just say no" campaign for drug use in America, often lacks depth and fails to consider broader factors such as historical context, political landscape, economic implications, and psychological aspects of human behavior. Such surface-level solutions may appear satisfactory but typically fall short in effectively resolving the core of the problem, leading to inadequate outcomes or unintended consequences. 

To genuinely address and resolve complex issues, a multidimensional approach that encompasses all underlying factors and their interconnections is crucial. This method ensures a more sustainable and comprehensive solution, avoiding the pitfalls of decisions based solely on oversimplified responses.

- What factors make this a difficult problem? 
- What are some of the complexities of this question? 
- What are some of the difficulties we need to deal with?

## Standards in depth : Breadth

To achieve a broad understanding of issues, it is crucial to consider all relevant viewpoints, especially those that oppose our own. Often, personal biases, limited education, and socio-centrism lead to narrow-minded thinking, where alternative perspectives are ignored or undervalued. 
For instance, in a domestic scenario where one spouse prefers to fall asleep with the TV on while the other struggles with it, recognizing and intellectually empathizing with the spouse's opposing view can lead to a broader understanding and a more equitable solution. Similarly, in heated debates like the morality of abortion, articulating each stance in detail—as seen by its proponents—without personal bias ensures a comprehensive grasp of the topic. 
This approach not only promotes intellectual fairness but also challenges self-serving behaviors by forcing consideration of differing viewpoints, thus fostering more balanced and informed decisions.

- How does that relate to the problem? 
- How does that bear on the question? 
- How does that help us with the issue?

## Standards in depth : Logicalness, Logical Consistency

Logical thinking necessitates the alignment and mutual support of combined thoughts. Often, humans unknowingly maintain contradictory beliefs, leading to inconsistencies in reasoning. For instance, despite evidence showing students' deficiencies in basic academic skills, teachers may illogically conclude that their teaching methods don't require modification. Similarly, a person advised by doctors to monitor their diet post-heart attack might illogically dismiss the importance of their eating habits. These examples highlight the common disconnect between evidence and conclusions drawn, underscoring the importance of critically evaluating our thought processes to ensure they are logical and consistent. Identifying and addressing illogical thinking in scenarios like educational settings or personal health decisions can prevent counterproductive outcomes and foster more rational decision-making.

- Does all of this make sense together? 
- Does your first paragraph fit in with your last?
- Does what you say follow from the evidence?

## Standards in depth : Significance

In both personal and professional contexts, there's a common tendency to concentrate on immediate, less important matters rather than on significant, impactful issues. This often leads to a misallocation of attention and resources, focusing on trivialities at the expense of truly meaningful objectives. For instance, students might prioritize grades over genuine learning, and individuals might dwell on superficial life details instead of profound life goals. To address this, it's crucial to identify and prioritize questions and actions that hold the most significance. Questions like "What does it mean to be an educated person?" or "What is the most important thing I could do in my life?" help steer focus towards substantial, impactful endeavors. Reflecting on how much time is spent on significant versus trivial pursuits can be a practical step towards redirecting efforts towards what truly matters, fostering a more purposeful and fulfilling approach to both personal growth and professional development.

- Is this the most important problem to consider? 
- Is this the central idea to focus on? 
- Which of these facts are the most important?

## Standards in depth : Fairness, Fair Thinking

Fair thinking involves rigorously evaluating our assumptions and decisions against the evidence available, ensuring that they are justified and unbiased. This process requires acknowledging the perspectives and rights of others, rather than allowing self-interest to skew our judgment. In practical scenarios, like the office temperature dispute between Kristi and Abbey, fair thinking mandates considering all relevant facts and viewpoints before drawing conclusions. Stereotypes and prejudices, such as broad generalizations about social groups, often lead to unjustified assumptions, which in turn result in erroneous and unfair conclusions. To cultivate fairness, one must actively challenge personal biases and self-serving tendencies by critically assessing the fairness of their thoughts and actions regularly. This introspection helps in identifying and correcting distortions in our thinking, thereby aligning our reasoning more closely with fairness and objectivity.

- Is my thinking justifiable in context? 
- Are my assumptions supported by evidence? 
- Is my purpose fair given the situation? 
- Am I using my concepts in keeping with educated usage or am I distorting them to get what I want?


Here is the input text / information : 

=== 
Summary of the topic or assumptions made by the speaker : 

{transcript_summary}

=== Summary of community people comments on the topic : 

{comments_summary}
"""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def evaluate_content(
        self, transcript_summary: str, comments_summary: str, config: PipelineConfig
    ) -> CriticalThinkingAssessment:
        """Evaluate content against critical thinking standards"""

        # Calculate input metrics
        input_chars = len((transcript_summary or "") + (comments_summary or ""))
        input_words = len((transcript_summary or "").split()) + len(
            (comments_summary or "").split()
        )
        estimated_input_tokens = input_chars // 4

        logger.info(
            f"Evaluating content using critical thinking standards with {config.gemini_model}"
        )
        logger.info("Evaluation input metrics:")
        logger.info(f"  - Combined characters: {input_chars:,}")
        logger.info(f"  - Combined words: {input_words:,}")
        logger.info(f"  - Estimated tokens: {estimated_input_tokens:,}")

        prompt = self.evaluation_prompt_template.format(
            transcript_summary=transcript_summary or "No transcript summary available.",
            comments_summary=comments_summary,
        )

        prompt_chars = len(prompt)
        estimated_prompt_tokens = prompt_chars // 4
        logger.info("Gemini evaluation prompt metrics:")
        logger.info(f"  - Total prompt characters: {prompt_chars:,}")
        logger.info(f"  - Estimated prompt tokens: {estimated_prompt_tokens:,}")

        generation_config = types.GenerateContentConfig(
            temperature=config.gemini_temperature,
            response_mime_type="application/json",
            response_schema=EvaluationResponse,
        )

        try:
            import time

            start_time = time.time()

            logger.info("Gemini API call starting (evaluation):")
            logger.info(f"  - Model: {config.gemini_model}")
            logger.info(f"  - Temperature: {config.gemini_temperature}")
            logger.info("  - Response format: JSON structured")

            response = self.client.models.generate_content(
                model=config.gemini_model,
                contents=prompt,
                config=generation_config,
            )

            # Calculate latency
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            evaluation_data = EvaluationResponse.model_validate_json(response.text)

            # Convert to our schema format
            standards = [
                CriticalThinkingStandard(
                    name=std.name,
                    evaluation=std.evaluation,
                    rating=std.rating,
                    followup_questions=std.followup_questions,
                )
                for std in evaluation_data.standards
            ]

            # Log output metrics
            output_chars = len(response.text)
            output_words = len(response.text.split())
            estimated_output_tokens = output_chars // 4

            logger.info("Gemini API call completed (evaluation):")
            logger.info(f"  - Latency: {latency_ms:.0f}ms")
            logger.info(f"  - Output characters: {output_chars:,}")
            logger.info(f"  - Output words: {output_words:,}")
            logger.info(f"  - Estimated output tokens: {estimated_output_tokens:,}")

            # Check if usage stats are available in response
            if hasattr(response, "usage") and response.usage:
                logger.info("Gemini token usage (actual, evaluation):")
                logger.info(f"  - Input tokens: {getattr(response.usage, 'input_tokens', 'N/A'):,}")
                logger.info(
                    f"  - Output tokens: {getattr(response.usage, 'output_tokens', 'N/A'):,}"
                )
                logger.info(f"  - Total tokens: {getattr(response.usage, 'total_tokens', 'N/A'):,}")
            else:
                logger.warning("Token usage data not available from Gemini response (evaluation)")

            # Select best questions
            selected_questions = self._select_best_questions(
                standards, config.num_selected_questions
            )
            logger.info(
                f"Selected {len(selected_questions)} priority questions from {len([q for s in standards for q in s.followup_questions])} total"
            )
            logger.info(f"Evaluation completed with {len(standards)} standards assessed")

            return CriticalThinkingAssessment(
                standards=standards,
                selected_questions=selected_questions,
                impact_scores=self._calculate_impact_scores(standards),
            )

        except Exception as e:
            logger.error(f"Google GenAI error during critical thinking evaluation: {e}")
            raise APIError(f"Critical thinking evaluation failed: {e}", "google_genai")

    def _select_best_questions(
        self, standards: List[CriticalThinkingStandard], num_questions: int
    ) -> List[str]:
        """Select the most impactful questions for follow-up"""

        # Create dataframe for analysis
        questions_data = []
        for standard in standards:
            for question in standard.followup_questions:
                questions_data.append(
                    {
                        "standard_name": standard.name,
                        "question": question,
                        "rating": standard.rating,
                        "impact_score": (10 - standard.rating) * 10,  # Lower rating = higher impact
                    }
                )

        if not questions_data:
            return []

        df = pd.DataFrame(questions_data)

        # Add category diversity bonus
        category_counts = df["standard_name"].value_counts()
        for category in df["standard_name"].unique():
            bonus = 50 / category_counts[category]
            df.loc[df["standard_name"] == category, "impact_score"] += bonus

        # Sort by impact score and select top questions
        df = df.sort_values("impact_score", ascending=False)

        # Ensure category diversity
        selected = []
        categories_covered = set()

        # First pass - one from each category
        for _, row in df.iterrows():
            if row["standard_name"] not in categories_covered and len(selected) < num_questions:
                selected.append(row["question"])
                categories_covered.add(row["standard_name"])

        # Second pass - highest impact remaining questions
        for _, row in df.iterrows():
            if row["question"] not in selected and len(selected) < num_questions:
                selected.append(row["question"])

        logger.info(f"Selected {len(selected)} priority questions from {len(questions_data)} total")
        return selected[:num_questions]

    def _calculate_impact_scores(
        self, standards: List[CriticalThinkingStandard]
    ) -> dict[str, float]:
        """Calculate impact scores for each standard"""
        scores = {}
        for standard in standards:
            # Lower ratings indicate more room for improvement
            impact_score = (10 - standard.rating) * 10
            scores[standard.name] = impact_score

        return scores
