from datetime import datetime
from typing import Tuple, Optional, List, Dict
import logging

# Configure logging
from blogi.core.config import logger

class ResearcherPostGenerator:
    def __init__(self, agent):
        self.agent = agent
        
    async def _load_templates(self) -> Dict[str, str]:
        templates = {}
        paths = {
            'agent_prompt': self.agent.agent_prompt_path,
            'enhanced_prompt': self.agent.enhanced_prompt_path,
            'disclaimer': self.agent.disclaimer_path,
            'frontmatter': self.agent.frontmatter_path,
            'blog_template': self.agent.blog_page_template_path,
            'summarize_content': self.agent.summarize_content_path
        }
        
        for name, path in paths.items():
            content = await self.agent.read_file(str(path))
            if not content:
                raise ValueError(f"Failed to load template: {name}")
            templates[name] = content
            
        return templates

    async def generate_blog_post(self) -> Tuple[str, str]:
        """Generate a research blog post.
        Returns:
            Tuple[str, str]: A tuple containing (filename, blog_page)
        """
        try:
            # Load templates and store them as instance variable
            self.templates = await self._load_templates()
            
            async with self.agent.web_service.get_session() as session:
                research_data = await self._gather_research()
                
                blog_content = await self.agent.anthropic.ask(
                    self._format_prompt(self.templates['agent_prompt'], research_data)
                )
                
                if not blog_content:
                    return "default.md", "Failed to generate content"
                    
                metadata = await self._generate_metadata(blog_content)
                pages = self._format_pages(self.templates, metadata, blog_content)
                
                filename = self._generate_filename(metadata['filename'])
                blog_page = pages['blog_page']
                
                return filename, blog_page
                
        except Exception as e:
            logger.error(f"Error generating researcher post: {str(e)}")
            return "error.md", f"Error generating post: {str(e)}"

    async def _gather_research(self) -> List[Dict]:
        try:
            search_results = await self.agent.brave_client.search(self.agent.topic)
            research_data = []
            
            for result in search_results[:3]:
                async with self.agent.web_service.get_session() as session:
                    content = await self.agent.web_service.fetch_webpage_content(result['url'])
                    if content:
                        summary = await self.agent.anthropic.ask(
                            self.templates['summarize_content'] + f"\n\n{content}"
                        )
                        research_data.append({
                            'title': result.get('title', ''),
                            'url': result.get('url', ''),
                            'description': result.get('description', ''),
                            'content_summary': summary
                        })
            
            return research_data
        except Exception as e:
            logger.error(f"Error in _gather_research: {str(e)}")
            raise

    def _format_research_summary(self, research_data: List[Dict]) -> str:
        return "\n\n".join([
            f"Source: {data['title']}\n"
            f"URL: {data['url']}\n\n"
            f"Description:\n{data['description']}\n\n"
            f"Detailed Summary:\n{data['content_summary'] or 'No summary available.'}"
            for data in research_data
        ])

    def _format_prompt(self, agent_prompt: str, research_data: List[Dict]) -> str:
        research_summary = self._format_research_summary(research_data)
        formatted_agent_prompt = agent_prompt.format(
            topic=self.agent.topic,
            today=datetime.now().strftime('%Y-%m-%d'),
            disclaimer=self.templates['disclaimer']
        )
        formatted_enhanced_prompt = self.templates['enhanced_prompt'].format(
            research_summary=research_summary,
            topic=self.agent.topic
        )
        return f"{formatted_agent_prompt}\n\n{formatted_enhanced_prompt}"

    async def _generate_metadata(self, content: str) -> Dict[str, str]:
        return {
            'title': await self.agent.generate_title(content),
            'tags': await self.agent.generate_tags(content),
            'filename': await self.agent.generate_filename(content),
            'date': datetime.now().strftime('%Y-%m-%d')
        }

    def _format_pages(self, templates: Dict[str, str], metadata: Dict[str, str], content: str) -> Dict[str, str]:
        frontmatter = templates['frontmatter'].format(
            title=metadata['title'],
            tags=metadata['tags'],
            date=metadata['date'],
            author="AI Agent Researcher"
        )

        return {
            'blog_page': templates['blog_template'].format(
                frontmatter=frontmatter,
                disclaimer=templates['disclaimer'],
                content=content
            )
        }

    def _generate_filename(self, filename: str) -> str:
        return f"{datetime.now().strftime('%Y-%m-%d')}-{filename}.md"
