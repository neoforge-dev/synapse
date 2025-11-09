#!/usr/bin/env python3
"""
Comprehensive LinkedIn Data Extractor for Synapse Integration

Processes 11,222+ posts, 5,222+ comments, and 10,749+ shares to extract:
- Ideas and concepts
- Beliefs and opinions
- Personal preferences
- Personal stories and experiences
- Controversial takes
- Business insights

For integration into Synapse vector store system.
"""

import csv
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExtractedBelief:
    """A belief or opinion extracted from content."""
    text: str
    confidence_level: str  # strong, moderate, mild
    category: str  # technical, career, business, personal
    source_type: str  # post, comment, share
    source_id: str
    context: str  # surrounding text for context
    date: datetime

@dataclass
class ExtractedIdea:
    """An idea or concept extracted from content."""
    concept: str
    description: str
    category: str  # technical, business, productivity, etc.
    applications: list[str]
    source_type: str
    source_id: str
    context: str
    date: datetime

@dataclass
class PersonalStory:
    """A personal story or experience."""
    title: str
    story_text: str
    lessons_learned: list[str]
    time_period: str  # when it happened
    category: str  # career, technical, business, personal
    source_type: str
    source_id: str
    date: datetime

@dataclass
class PersonalPreference:
    """A personal preference about tools, methods, etc."""
    preference_type: str  # tool, methodology, approach, etc.
    preferred_option: str
    reasoning: str
    category: str
    source_type: str
    source_id: str
    context: str
    date: datetime

@dataclass
class ControversialTake:
    """A controversial opinion or contrarian view."""
    statement: str
    controversy_level: str  # high, medium, low
    topic_area: str
    reasoning: str
    source_type: str
    source_id: str
    engagement_indicators: dict[str, int]  # likes, comments, shares
    date: datetime

class ComprehensiveLinkedInExtractor:
    """Extracts comprehensive insights from LinkedIn export data."""

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.post_stats_file = self.data_dir.parent / "LinkedInPost stats.csv"

        # Extracted data storage
        self.beliefs: list[ExtractedBelief] = []
        self.ideas: list[ExtractedIdea] = []
        self.stories: list[PersonalStory] = []
        self.preferences: list[PersonalPreference] = []
        self.controversial_takes: list[ControversialTake] = []

        # Pattern matching for extraction
        self._setup_extraction_patterns()

    def _setup_extraction_patterns(self):
        """Setup regex patterns for extracting different types of content."""

        # Belief patterns
        self.belief_patterns = {
            'strong': [
                r"I believe that?\s+(.+?)(?:\.|$)",
                r"My conviction is\s+(.+?)(?:\.|$)",
                r"I'm convinced that?\s+(.+?)(?:\.|$)",
                r"The truth is\s+(.+?)(?:\.|$)",
                r"Without a doubt,?\s+(.+?)(?:\.|$)"
            ],
            'moderate': [
                r"I think that?\s+(.+?)(?:\.|$)",
                r"In my opinion,?\s+(.+?)(?:\.|$)",
                r"I've found that?\s+(.+?)(?:\.|$)",
                r"My experience suggests\s+(.+?)(?:\.|$)",
                r"It seems to me\s+(.+?)(?:\.|$)"
            ],
            'mild': [
                r"I tend to think\s+(.+?)(?:\.|$)",
                r"I'm inclined to believe\s+(.+?)(?:\.|$)",
                r"It appears that?\s+(.+?)(?:\.|$)",
                r"I suspect\s+(.+?)(?:\.|$)"
            ]
        }

        # Personal story patterns
        self.story_patterns = [
            r"(?:Years? ago|Last year|Recently|When I|Back when|During my time|In my experience at)\s+(.+?)(?:\n\n|\. [A-Z])",
            r"I remember when\s+(.+?)(?:\n\n|\. [A-Z])",
            r"Let me tell you about\s+(.+?)(?:\n\n|\. [A-Z])",
            r"Here's what happened\s+(.+?)(?:\n\n|\. [A-Z])",
            r"My journey\s+(.+?)(?:\n\n|\. [A-Z])"
        ]

        # Preference patterns
        self.preference_patterns = [
            r"I prefer\s+(.+?)\s+(?:over|to|because|since)\s+(.+?)(?:\.|$)",
            r"My go-to\s+(.+?)\s+is\s+(.+?)(?:\.|$)",
            r"I always use\s+(.+?)(?:\.|$)",
            r"(?:The best|My favorite)\s+(.+?)\s+is\s+(.+?)(?:\.|$)",
            r"I recommend\s+(.+?)\s+(?:over|instead of)\s+(.+?)(?:\.|$)"
        ]

        # Controversial opinion patterns
        self.controversial_patterns = [
            r"Unpopular opinion:?\s+(.+?)(?:\n|\.|$)",
            r"Controversial take:?\s+(.+?)(?:\n|\.|$)",
            r"(?:Most people|Everyone) (?:thinks?|believes?|says?)\s+(.+?),?\s+but\s+(.+?)(?:\.|$)",
            r"The problem with\s+(.+?)\s+is\s+(.+?)(?:\.|$)",
            r"(?:I disagree|I don't buy|I don't believe)\s+(.+?)(?:\.|$)",
            r"(?:The truth|Reality) is\s+(.+?)(?:\.|$)"
        ]

        # Idea/concept patterns
        self.idea_patterns = [
            r"(?:Here's|This is) (?:a|an|the)\s+(.+?)\s+(?:that|which|to)\s+(.+?)(?:\.|$)",
            r"(?:The key|Secret|Trick) (?:is|to)\s+(.+?)(?:\.|$)",
            r"(?:Framework|Method|Approach|Strategy)(?:\s+I use)?\s*:?\s+(.+?)(?:\.|$)",
            r"(?:What works|What I do|My approach) (?:is|for)\s+(.+?)(?:\.|$)"
        ]

    def process_all_linkedin_data(self):
        """Process all LinkedIn data files."""
        logger.info("Starting comprehensive LinkedIn data extraction...")

        # Process posts
        self._process_posts()

        # Process comments
        self._process_comments()

        # Process shares
        self._process_shares()

        # Generate summary
        self._generate_extraction_summary()

    def _process_posts(self):
        """Process LinkedIn posts from the stats file."""
        if not self.post_stats_file.exists():
            logger.error(f"Post stats file not found: {self.post_stats_file}")
            return

        logger.info(f"Processing posts from {self.post_stats_file}")

        posts_processed = 0
        with open(self.post_stats_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                if not row.get('text'):
                    continue

                posts_processed += 1
                if posts_processed % 1000 == 0:
                    logger.info(f"Processed {posts_processed} posts...")

                post_text = row['text']
                post_id = row.get('urn', f"post_{posts_processed}")
                created_at = self._parse_date(row.get('createdAt (TZ=Europe/Bucharest)', ''))

                # Extract engagement metrics for controversial take ranking
                engagement = {
                    'reactions': int(row.get('numReactions', 0)),
                    'comments': int(row.get('numComments', 0)),
                    'shares': int(row.get('numShares', 0))
                }

                # Extract different types of content
                self._extract_beliefs_from_text(post_text, 'post', post_id, created_at)
                self._extract_ideas_from_text(post_text, 'post', post_id, created_at)
                self._extract_stories_from_text(post_text, 'post', post_id, created_at)
                self._extract_preferences_from_text(post_text, 'post', post_id, created_at)
                self._extract_controversial_takes_from_text(post_text, 'post', post_id, created_at, engagement)

        logger.info(f"Processed {posts_processed} posts")

    def _process_comments(self):
        """Process LinkedIn comments."""
        comments_file = self.data_dir / "Comments.csv"
        if not comments_file.exists():
            logger.warning(f"Comments file not found: {comments_file}")
            return

        logger.info(f"Processing comments from {comments_file}")

        comments_processed = 0
        try:
            with open(comments_file, encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    if not row.get('Message'):
                        continue

                    comments_processed += 1
                    if comments_processed % 500 == 0:
                        logger.info(f"Processed {comments_processed} comments...")

                    comment_text = row['Message']
                    comment_id = f"comment_{comments_processed}"

                    # Try to parse date, but handle malformed entries
                    try:
                        created_at = datetime.strptime(row['Date'], '%Y-%m-%d %H:%M:%S')
                    except (ValueError, KeyError, TypeError) as e:
                        created_at = datetime.now()

                    # Comments often contain quick beliefs and preferences
                    self._extract_beliefs_from_text(comment_text, 'comment', comment_id, created_at)
                    self._extract_preferences_from_text(comment_text, 'comment', comment_id, created_at)

        except Exception as e:
            logger.error(f"Error processing comments: {e}")

        logger.info(f"Processed {comments_processed} comments")

    def _process_shares(self):
        """Process LinkedIn shares."""
        shares_file = self.data_dir / "Shares.csv"
        if not shares_file.exists():
            logger.warning(f"Shares file not found: {shares_file}")
            return

        logger.info(f"Processing shares from {shares_file}")

        shares_processed = 0
        try:
            with open(shares_file, encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    if not row.get('ShareCommentary'):
                        continue

                    shares_processed += 1
                    if shares_processed % 500 == 0:
                        logger.info(f"Processed {shares_processed} shares...")

                    share_text = row['ShareCommentary']
                    share_id = f"share_{shares_processed}"
                    created_at = self._parse_date(row.get('Date', ''))

                    # Shares often contain opinions and recommendations
                    self._extract_beliefs_from_text(share_text, 'share', share_id, created_at)
                    self._extract_ideas_from_text(share_text, 'share', share_id, created_at)

        except Exception as e:
            logger.error(f"Error processing shares: {e}")

        logger.info(f"Processed {shares_processed} shares")

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string with fallback."""
        if not date_str:
            return datetime.now()

        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m-%d-%Y'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue

        return datetime.now()

    def _extract_beliefs_from_text(self, text: str, source_type: str, source_id: str, date: datetime):
        """Extract beliefs and opinions from text."""
        for confidence, patterns in self.belief_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    belief_text = match.group(1).strip()
                    if len(belief_text) > 10:  # Filter out very short beliefs

                        # Categorize the belief
                        category = self._categorize_belief(belief_text)

                        # Extract context (50 chars before and after)
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end].strip()

                        belief = ExtractedBelief(
                            text=belief_text,
                            confidence_level=confidence,
                            category=category,
                            source_type=source_type,
                            source_id=source_id,
                            context=context,
                            date=date
                        )
                        self.beliefs.append(belief)

    def _extract_ideas_from_text(self, text: str, source_type: str, source_id: str, date: datetime):
        """Extract ideas and concepts from text."""
        for pattern in self.idea_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if len(match.groups()) >= 1:
                    concept = match.group(1).strip()
                    description = match.group(2).strip() if len(match.groups()) > 1 else ""

                    if len(concept) > 5:  # Filter out very short concepts
                        category = self._categorize_idea(concept + " " + description)

                        # Extract context
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end].strip()

                        idea = ExtractedIdea(
                            concept=concept,
                            description=description,
                            category=category,
                            applications=self._extract_applications(description),
                            source_type=source_type,
                            source_id=source_id,
                            context=context,
                            date=date
                        )
                        self.ideas.append(idea)

    def _extract_stories_from_text(self, text: str, source_type: str, source_id: str, date: datetime):
        """Extract personal stories and experiences."""
        for pattern in self.story_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            for match in matches:
                story_text = match.group(1).strip()

                if len(story_text) > 50:  # Filter out very short stories
                    # Try to extract lessons learned
                    lessons = self._extract_lessons_from_story(story_text)

                    # Categorize the story
                    category = self._categorize_story(story_text)

                    # Extract time period
                    time_period = self._extract_time_period(match.group(0))

                    story = PersonalStory(
                        title=self._generate_story_title(story_text),
                        story_text=story_text,
                        lessons_learned=lessons,
                        time_period=time_period,
                        category=category,
                        source_type=source_type,
                        source_id=source_id,
                        date=date
                    )
                    self.stories.append(story)

    def _extract_preferences_from_text(self, text: str, source_type: str, source_id: str, date: datetime):
        """Extract personal preferences."""
        for pattern in self.preference_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 1:
                    preferred_option = match.group(1).strip()
                    reasoning = match.group(2).strip() if len(match.groups()) > 1 else ""

                    if len(preferred_option) > 3:
                        category = self._categorize_preference(preferred_option)
                        preference_type = self._determine_preference_type(preferred_option)

                        # Extract context
                        start = max(0, match.start() - 30)
                        end = min(len(text), match.end() + 30)
                        context = text[start:end].strip()

                        preference = PersonalPreference(
                            preference_type=preference_type,
                            preferred_option=preferred_option,
                            reasoning=reasoning,
                            category=category,
                            source_type=source_type,
                            source_id=source_id,
                            context=context,
                            date=date
                        )
                        self.preferences.append(preference)

    def _extract_controversial_takes_from_text(self, text: str, source_type: str, source_id: str,
                                             date: datetime, engagement: dict[str, int]):
        """Extract controversial opinions."""
        for pattern in self.controversial_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if len(match.groups()) >= 1:
                    statement = match.group(1).strip()

                    if len(statement) > 10:
                        # Determine controversy level based on engagement
                        controversy_level = self._assess_controversy_level(engagement)

                        # Extract reasoning if available
                        reasoning = match.group(2).strip() if len(match.groups()) > 1 else ""

                        topic_area = self._categorize_controversial_topic(statement)

                        controversial_take = ControversialTake(
                            statement=statement,
                            controversy_level=controversy_level,
                            topic_area=topic_area,
                            reasoning=reasoning,
                            source_type=source_type,
                            source_id=source_id,
                            engagement_indicators=engagement,
                            date=date
                        )
                        self.controversial_takes.append(controversial_take)

    def _categorize_belief(self, belief_text: str) -> str:
        """Categorize a belief into technical, career, business, or personal."""
        belief_lower = belief_text.lower()

        technical_keywords = ['code', 'programming', 'software', 'development', 'architecture', 'framework', 'api', 'database']
        career_keywords = ['career', 'job', 'growth', 'learning', 'skill', 'experience', 'developer', 'engineer']
        business_keywords = ['startup', 'business', 'company', 'team', 'management', 'leadership', 'strategy']

        if any(kw in belief_lower for kw in technical_keywords):
            return 'technical'
        elif any(kw in belief_lower for kw in career_keywords):
            return 'career'
        elif any(kw in belief_lower for kw in business_keywords):
            return 'business'
        else:
            return 'personal'

    def _categorize_idea(self, idea_text: str) -> str:
        """Categorize an idea."""
        idea_lower = idea_text.lower()

        if any(kw in idea_lower for kw in ['framework', 'method', 'approach', 'strategy', 'system']):
            return 'methodology'
        elif any(kw in idea_lower for kw in ['tool', 'library', 'service', 'platform']):
            return 'technical'
        elif any(kw in idea_lower for kw in ['team', 'management', 'leadership', 'culture']):
            return 'business'
        elif any(kw in idea_lower for kw in ['productivity', 'efficiency', 'optimization']):
            return 'productivity'
        else:
            return 'general'

    def _categorize_story(self, story_text: str) -> str:
        """Categorize a personal story."""
        story_lower = story_text.lower()

        if any(kw in story_lower for kw in ['career', 'job', 'hired', 'interview', 'promotion']):
            return 'career'
        elif any(kw in story_lower for kw in ['project', 'code', 'bug', 'development', 'programming']):
            return 'technical'
        elif any(kw in story_lower for kw in ['startup', 'company', 'team', 'business', 'client']):
            return 'business'
        else:
            return 'personal'

    def _categorize_preference(self, preference_text: str) -> str:
        """Categorize a preference."""
        pref_lower = preference_text.lower()

        if any(kw in pref_lower for kw in ['language', 'framework', 'library', 'tool', 'ide', 'editor']):
            return 'technical'
        elif any(kw in pref_lower for kw in ['methodology', 'process', 'approach', 'practice']):
            return 'process'
        elif any(kw in pref_lower for kw in ['management', 'communication', 'meeting']):
            return 'management'
        else:
            return 'general'

    def _determine_preference_type(self, preference_text: str) -> str:
        """Determine the type of preference."""
        pref_lower = preference_text.lower()

        if any(kw in pref_lower for kw in ['python', 'javascript', 'java', 'language']):
            return 'programming_language'
        elif any(kw in pref_lower for kw in ['framework', 'library', 'package']):
            return 'technology_stack'
        elif any(kw in pref_lower for kw in ['tool', 'editor', 'ide']):
            return 'development_tool'
        elif any(kw in pref_lower for kw in ['method', 'approach', 'practice']):
            return 'methodology'
        else:
            return 'general'

    def _categorize_controversial_topic(self, statement: str) -> str:
        """Categorize controversial topic area."""
        stmt_lower = statement.lower()

        if any(kw in stmt_lower for kw in ['microservices', 'monolith', 'architecture', 'design']):
            return 'architecture'
        elif any(kw in stmt_lower for kw in ['language', 'framework', 'technology', 'tool']):
            return 'technology_choice'
        elif any(kw in stmt_lower for kw in ['testing', 'tdd', 'quality', 'code review']):
            return 'development_practice'
        elif any(kw in stmt_lower for kw in ['management', 'leadership', 'team', 'culture']):
            return 'management_practice'
        else:
            return 'general_opinion'

    def _assess_controversy_level(self, engagement: dict[str, int]) -> str:
        """Assess controversy level based on engagement."""
        total_engagement = sum(engagement.values())
        comment_ratio = engagement.get('comments', 0) / max(total_engagement, 1)

        if comment_ratio > 0.3 and total_engagement > 50:
            return 'high'
        elif comment_ratio > 0.2 and total_engagement > 20:
            return 'medium'
        else:
            return 'low'

    def _extract_applications(self, description: str) -> list[str]:
        """Extract potential applications from description."""
        # Simple heuristic - look for "for", "in", "when" patterns
        applications = []
        app_patterns = [
            r"for\s+(.+?)(?:\.|,|$)",
            r"in\s+(.+?)(?:\.|,|$)",
            r"when\s+(.+?)(?:\.|,|$)"
        ]

        for pattern in app_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            applications.extend([match.strip() for match in matches])

        return applications[:3]  # Limit to 3 applications

    def _extract_lessons_from_story(self, story_text: str) -> list[str]:
        """Extract lessons learned from a story."""
        lessons = []
        lesson_patterns = [
            r"(?:learned|discovered|realized|found out)\s+that\s+(.+?)(?:\.|$)",
            r"(?:lesson|takeaway|key point)\s+(?:is|was)\s+(.+?)(?:\.|$)",
            r"(?:what I learned|key insight)\s+(.+?)(?:\.|$)"
        ]

        for pattern in lesson_patterns:
            matches = re.findall(pattern, story_text, re.IGNORECASE)
            lessons.extend([match.strip() for match in matches])

        return lessons[:3]  # Limit to 3 lessons

    def _extract_time_period(self, text: str) -> str:
        """Extract time period from story text."""
        time_patterns = [
            r"(\d+)\s+years?\s+ago",
            r"(last\s+year|recently|when\s+I|back\s+when|during\s+my\s+time)",
            r"in\s+(\d{4})",
            r"(early|mid|late)\s+career"
        ]

        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return "unspecified"

    def _generate_story_title(self, story_text: str) -> str:
        """Generate a title for the story."""
        # Take first sentence or first 50 characters
        sentences = story_text.split('.')
        if sentences and len(sentences[0]) < 80:
            return sentences[0].strip()
        else:
            return story_text[:50] + "..." if len(story_text) > 50 else story_text

    def _generate_extraction_summary(self):
        """Generate summary of extraction results."""
        logger.info("=== Extraction Summary ===")
        logger.info(f"Beliefs extracted: {len(self.beliefs)}")
        logger.info(f"Ideas extracted: {len(self.ideas)}")
        logger.info(f"Personal stories extracted: {len(self.stories)}")
        logger.info(f"Preferences extracted: {len(self.preferences)}")
        logger.info(f"Controversial takes extracted: {len(self.controversial_takes)}")

        # Category breakdown
        belief_categories = Counter(belief.category for belief in self.beliefs)
        logger.info(f"Belief categories: {dict(belief_categories)}")

        story_categories = Counter(story.category for story in self.stories)
        logger.info(f"Story categories: {dict(story_categories)}")

        controversial_topics = Counter(take.topic_area for take in self.controversial_takes)
        logger.info(f"Controversial topics: {dict(controversial_topics)}")

    def export_for_synapse_ingestion(self, output_dir: str):
        """Export extracted data in format suitable for Synapse ingestion."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # Export beliefs
        beliefs_data = []
        for belief in self.beliefs:
            beliefs_data.append({
                "id": f"belief_{len(beliefs_data)}",
                "content": f"**Belief ({belief.confidence_level})**: {belief.text}",
                "metadata": {
                    "type": "belief",
                    "category": belief.category,
                    "confidence_level": belief.confidence_level,
                    "source_type": belief.source_type,
                    "source_id": belief.source_id,
                    "date": belief.date.isoformat(),
                    "context": belief.context
                }
            })

        # Export ideas
        ideas_data = []
        for idea in self.ideas:
            content = f"**Idea - {idea.concept}**: {idea.description}"
            if idea.applications:
                content += f" Applications: {', '.join(idea.applications)}"

            ideas_data.append({
                "id": f"idea_{len(ideas_data)}",
                "content": content,
                "metadata": {
                    "type": "idea",
                    "concept": idea.concept,
                    "category": idea.category,
                    "applications": idea.applications,
                    "source_type": idea.source_type,
                    "source_id": idea.source_id,
                    "date": idea.date.isoformat(),
                    "context": idea.context
                }
            })

        # Export stories
        stories_data = []
        for story in self.stories:
            content = f"**Personal Story - {story.title}**: {story.story_text}"
            if story.lessons_learned:
                content += f" Lessons: {', '.join(story.lessons_learned)}"

            stories_data.append({
                "id": f"story_{len(stories_data)}",
                "content": content,
                "metadata": {
                    "type": "personal_story",
                    "title": story.title,
                    "category": story.category,
                    "time_period": story.time_period,
                    "lessons_learned": story.lessons_learned,
                    "source_type": story.source_type,
                    "source_id": story.source_id,
                    "date": story.date.isoformat()
                }
            })

        # Export preferences
        preferences_data = []
        for pref in self.preferences:
            content = f"**Preference - {pref.preference_type}**: Prefers {pref.preferred_option}"
            if pref.reasoning:
                content += f" Reasoning: {pref.reasoning}"

            preferences_data.append({
                "id": f"preference_{len(preferences_data)}",
                "content": content,
                "metadata": {
                    "type": "preference",
                    "preference_type": pref.preference_type,
                    "preferred_option": pref.preferred_option,
                    "category": pref.category,
                    "reasoning": pref.reasoning,
                    "source_type": pref.source_type,
                    "source_id": pref.source_id,
                    "date": pref.date.isoformat(),
                    "context": pref.context
                }
            })

        # Export controversial takes
        controversial_data = []
        for take in self.controversial_takes:
            content = f"**Controversial Take ({take.controversy_level})**: {take.statement}"
            if take.reasoning:
                content += f" Reasoning: {take.reasoning}"

            controversial_data.append({
                "id": f"controversial_{len(controversial_data)}",
                "content": content,
                "metadata": {
                    "type": "controversial_take",
                    "statement": take.statement,
                    "controversy_level": take.controversy_level,
                    "topic_area": take.topic_area,
                    "reasoning": take.reasoning,
                    "engagement_indicators": take.engagement_indicators,
                    "source_type": take.source_type,
                    "source_id": take.source_id,
                    "date": take.date.isoformat()
                }
            })

        # Save all data files
        datasets = {
            "beliefs": beliefs_data,
            "ideas": ideas_data,
            "personal_stories": stories_data,
            "preferences": preferences_data,
            "controversial_takes": controversial_data
        }

        for dataset_name, data in datasets.items():
            file_path = output_path / f"linkedin_{dataset_name}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Exported {len(data)} {dataset_name} to {file_path}")

        # Create combined dataset for Synapse ingestion
        all_data = []
        for dataset_data in datasets.values():
            all_data.extend(dataset_data)

        combined_path = output_path / "linkedin_comprehensive_dataset.json"
        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Created comprehensive dataset with {len(all_data)} items: {combined_path}")

        # Generate ingestion summary
        summary = {
            "extraction_date": datetime.now().isoformat(),
            "total_items_extracted": len(all_data),
            "breakdown": {
                "beliefs": len(beliefs_data),
                "ideas": len(ideas_data),
                "personal_stories": len(stories_data),
                "preferences": len(preferences_data),
                "controversial_takes": len(controversial_data)
            },
            "category_breakdown": {
                "beliefs": dict(Counter(item["metadata"]["category"] for item in beliefs_data)),
                "stories": dict(Counter(item["metadata"]["category"] for item in stories_data)),
                "controversial_topics": dict(Counter(item["metadata"]["topic_area"] for item in controversial_data))
            },
            "ready_for_synapse_ingestion": True,
            "recommended_ingestion_command": f"uv run python -m graph_rag.cli.main ingest {combined_path}"
        }

        summary_path = output_path / "extraction_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"Extraction summary saved: {summary_path}")
        return summary, combined_path


def main():
    """Main execution function."""
    data_dir = "/Users/bogdan/data/Complete_LinkedInDataExport_10-18-2024"
    output_dir = "/Users/bogdan/til/graph-rag-mcp/data/linkedin_extracted"

    extractor = ComprehensiveLinkedInExtractor(data_dir)

    print("🔍 Comprehensive LinkedIn Data Extraction")
    print("=" * 60)
    print("📊 Processing 11,222+ posts, 5,222+ comments, 10,749+ shares")
    print("🎯 Extracting: beliefs, ideas, stories, preferences, controversial takes")
    print()

    # Process all data
    extractor.process_all_linkedin_data()

    # Export for Synapse ingestion
    summary, dataset_path = extractor.export_for_synapse_ingestion(output_dir)

    print("\n✅ Extraction Complete!")
    print("=" * 60)
    print(f"📊 Total items extracted: {summary['total_items_extracted']}")
    print(f"💭 Beliefs: {summary['breakdown']['beliefs']}")
    print(f"💡 Ideas: {summary['breakdown']['ideas']}")
    print(f"📖 Personal stories: {summary['breakdown']['personal_stories']}")
    print(f"⚙️  Preferences: {summary['breakdown']['preferences']}")
    print(f"⚡ Controversial takes: {summary['breakdown']['controversial_takes']}")
    print()
    print(f"📁 Dataset ready for Synapse: {dataset_path}")
    print(f"🚀 Ingestion command: {summary['recommended_ingestion_command']}")

    return extractor, summary, dataset_path


if __name__ == "__main__":
    main()
