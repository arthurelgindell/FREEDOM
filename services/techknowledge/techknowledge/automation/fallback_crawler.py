"""
Fallback Crawler - Simple GitHub README crawler for testing
Used when Firecrawl API is unavailable
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, Any
import hashlib

logger = logging.getLogger(__name__)


class FallbackCrawler:
    """Simple crawler for GitHub README files when Firecrawl is unavailable"""

    async def crawl_github_readme(self, github_url: str) -> Dict[str, Any]:
        """Crawl GitHub README and extract basic content"""

        logger.info(f"📄 Fallback crawling: {github_url}")

        try:
            # Convert GitHub blob URL to raw URL
            if "github.com" in github_url and "/blob/" in github_url:
                raw_url = github_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            else:
                raw_url = github_url

            async with aiohttp.ClientSession() as session:
                async with session.get(raw_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.text()

                        # Calculate content hash
                        content_hash = hashlib.sha256(content.encode()).hexdigest()

                        # Extract basic technical information (simple parsing)
                        extracted_specs = self._extract_basic_specs(content)

                        logger.info(f"✅ Fallback crawl successful: {len(content)} chars")

                        return {
                            "success": True,
                            "content": {
                                "technical_specifications": extracted_specs,
                                "raw_content": content
                            },
                            "content_hash": content_hash,
                            "raw_markdown": content,
                            "metadata": {
                                "url": github_url,
                                "crawled_at": datetime.now().isoformat(),
                                "crawler": "fallback",
                                "extraction_method": "basic_parsing"
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"HTTP {response.status}",
                            "content": None
                        }

        except Exception as e:
            logger.error(f"❌ Fallback crawl failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }

    def _extract_basic_specs(self, markdown_content: str) -> list:
        """Extract basic technical specifications from markdown"""

        specs = []
        lines = markdown_content.split('\n')

        # Look for code blocks and commands
        in_code_block = False
        current_block = []

        for line in lines:
            if line.strip().startswith('```'):
                if in_code_block:
                    # End of code block
                    if current_block:
                        code_content = '\n'.join(current_block)
                        if self._is_technical_content(code_content):
                            specs.append({
                                "component_type": "code",
                                "component_name": "code_block",
                                "specification": {"code": code_content},
                                "source_section": "readme"
                            })
                    current_block = []
                    in_code_block = False
                else:
                    in_code_block = True
            elif in_code_block:
                current_block.append(line)
            else:
                # Look for command-like patterns
                if self._looks_like_command(line):
                    specs.append({
                        "component_type": "command",
                        "component_name": "installation_or_usage",
                        "specification": {"command": line.strip()},
                        "source_section": "readme"
                    })

        return specs

    def _is_technical_content(self, content: str) -> bool:
        """Check if content appears to be technical"""
        technical_keywords = [
            'import', 'function', 'class', 'def', 'var', 'const',
            'package', 'module', 'config', 'install', 'run',
            'api', 'http', 'json', 'xml', 'sql', 'curl'
        ]
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in technical_keywords)

    def _looks_like_command(self, line: str) -> bool:
        """Check if line looks like a command"""
        line = line.strip()
        command_prefixes = ['$', '>', 'npm ', 'pip ', 'go ', 'cargo ', 'git ', 'curl ', 'wget ']
        return any(line.startswith(prefix) for prefix in command_prefixes)


# Test the fallback crawler
async def test_fallback_crawler():
    """Test fallback crawler"""

    print("🧪 FALLBACK CRAWLER TEST")
    print("=" * 30)

    crawler = FallbackCrawler()

    test_url = "https://github.com/charmbracelet/crush/blob/main/README.md"
    result = await crawler.crawl_github_readme(test_url)

    if result["success"]:
        print(f"✅ Crawled: {test_url}")
        specs = result["content"]["technical_specifications"]
        print(f"📊 Extracted {len(specs)} technical specifications")

        for i, spec in enumerate(specs[:3]):  # Show first 3
            print(f"   {i+1}. {spec['component_type']}: {spec['component_name']}")

        return True
    else:
        print(f"❌ Crawl failed: {result['error']}")
        return False


if __name__ == "__main__":
    asyncio.run(test_fallback_crawler())