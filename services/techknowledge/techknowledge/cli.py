#!/usr/bin/env python3
"""
TechKnowledge CLI - Command-line interface for manual operations
"""

import asyncio
import sys
import argparse
from datetime import datetime

from .automation.complete_pipeline import CompleteTechKnowledgePipeline
from .automation.pipeline_orchestrator import TechKnowledgePipeline
from .api.query import TechKnowledgeQuery


class TechKnowledgeCLI:
    """Command-line interface for TechKnowledge operations"""

    def __init__(self):
        self.pipeline = CompleteTechKnowledgePipeline()
        self.orchestrator = TechKnowledgePipeline()

    async def process_all(self):
        """Process all pending technologies"""
        print("🚀 Processing all pending technologies...")

        result = await self.pipeline.run_full_pipeline()

        if result["success"]:
            print(f"✅ Success: {result['message']}")
            for tech_result in result.get("results", []):
                status = "✅" if tech_result["success"] else "❌"
                print(f"   {status} {tech_result['technology']}: {tech_result['message']}")
        else:
            print(f"❌ Failed: {result['message']}")

        return result["success"]

    async def process_technology(self, tech_name: str):
        """Process a specific technology"""
        print(f"🔧 Processing technology: {tech_name}")

        # Reset the technology to unprocessed state
        conn = self.orchestrator.get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                UPDATE crawl_sources
                SET last_crawled = NULL, last_success = NULL
                WHERE technology_id IN (
                    SELECT id FROM technologies WHERE name = %s
                )
            """, (tech_name,))

            if cur.rowcount == 0:
                print(f"❌ Technology '{tech_name}' not found")
                return False

            conn.commit()
            print(f"🔄 Reset {tech_name} to unprocessed state")

        finally:
            cur.close()
            conn.close()

        # Process the technology
        result = await self.pipeline.run_full_pipeline()

        if result["success"] and result["successful"] > 0:
            tech_result = next((r for r in result["results"] if r["technology"] == tech_name), None)
            if tech_result:
                if tech_result["success"]:
                    print(f"✅ {tech_name}: {tech_result['message']}")
                    return True
                else:
                    print(f"❌ {tech_name}: {tech_result['message']}")
                    return False

        print(f"❌ Failed to process {tech_name}")
        return False

    async def show_status(self):
        """Show system status"""
        print("📊 TechKnowledge System Status")
        print("=" * 50)

        status = await self.pipeline.get_system_status()

        if "error" in status:
            print(f"❌ Error getting status: {status['error']}")
            return False

        # Pipeline status
        pipeline = status["pipeline"]
        print(f"\n🔧 PIPELINE STATUS:")
        print(f"   Total technologies: {pipeline['total_technologies']}")
        print(f"   Pending: {pipeline['pending']}")
        print(f"   Completed: {pipeline['completed']}")
        print(f"   Failed: {pipeline['failed']}")
        print(f"   Completion rate: {pipeline['completion_rate']:.1f}%")

        # API status
        apis = status["apis"]
        print(f"\n🌐 API STATUS:")
        print(f"   Firecrawl API: {'✅ Connected' if apis['firecrawl'] else '❌ Unavailable'}")
        print(f"   Fallback crawler: ✅ Available")

        # Database status
        db = status["database"]
        print(f"\n💾 DATABASE STATUS:")
        print(f"   Specifications: {db['specifications']}")
        print(f"   Decontamination logs: {db['decontamination_logs']}")

        # System readiness
        print(f"\n🎯 SYSTEM READY: {'✅ Yes' if status['system_ready'] else '❌ No'}")

        return True

    async def query_specifications(self, technology: str, component: str = None):
        """Query specifications for a technology"""
        print(f"🔍 Querying specifications for: {technology}")

        try:
            # This would use the query API when it's fully integrated
            conn = self.orchestrator.get_db_connection()
            cur = conn.cursor()

            if component:
                cur.execute("""
                    SELECT component_type, component_name, specification, confidence_score
                    FROM specifications s
                    JOIN technologies t ON s.technology_id = t.id
                    WHERE t.name = %s AND s.component_name ILIKE %s
                    ORDER BY confidence_score DESC
                    LIMIT 10
                """, (technology, f"%{component}%"))
            else:
                cur.execute("""
                    SELECT component_type, component_name, specification, confidence_score
                    FROM specifications s
                    JOIN technologies t ON s.technology_id = t.id
                    WHERE t.name = %s
                    ORDER BY confidence_score DESC
                    LIMIT 10
                """, (technology,))

            results = cur.fetchall()

            if results:
                print(f"\n📋 Found {len(results)} specifications:")
                for comp_type, comp_name, spec_data, confidence in results:
                    print(f"\n   🔹 {comp_type}: {comp_name} (confidence: {confidence:.2f})")
                    if isinstance(spec_data, str):
                        import json
                        try:
                            spec_data = json.loads(spec_data)
                        except:
                            pass

                    if isinstance(spec_data, dict):
                        for key, value in list(spec_data.items())[:3]:  # Show first 3 keys
                            print(f"      {key}: {str(value)[:100]}...")
                    else:
                        print(f"      {str(spec_data)[:150]}...")
            else:
                print(f"❌ No specifications found for '{technology}'")
                if component:
                    print(f"   (searched for component: {component})")

            cur.close()
            conn.close()

            return len(results) > 0

        except Exception as e:
            print(f"❌ Query failed: {e}")
            return False

    async def list_technologies(self):
        """List all registered technologies"""
        print("📋 Registered Technologies")
        print("=" * 30)

        conn = self.orchestrator.get_db_connection()
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT t.name, t.category,
                       CASE WHEN cs.last_success IS NOT NULL THEN 'Processed'
                            WHEN cs.last_crawled IS NOT NULL THEN 'Crawled'
                            ELSE 'Pending' END as status,
                       COUNT(s.id) as spec_count
                FROM technologies t
                LEFT JOIN crawl_sources cs ON t.id = cs.technology_id
                LEFT JOIN specifications s ON t.id = s.technology_id
                WHERE t.active = true
                GROUP BY t.id, t.name, t.category, cs.last_success, cs.last_crawled
                ORDER BY t.name
            """)

            results = cur.fetchall()

            if results:
                for name, category, status, spec_count in results:
                    status_icon = {"Processed": "✅", "Crawled": "🔄", "Pending": "⏳"}.get(status, "❓")
                    print(f"   {status_icon} {name} ({category}) - {status} - {spec_count} specs")
            else:
                print("   No technologies registered")

            cur.close()
            conn.close()

            return len(results) > 0

        except Exception as e:
            print(f"❌ Failed to list technologies: {e}")
            return False


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="TechKnowledge CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Process commands
    process_parser = subparsers.add_parser("process", help="Process technologies")
    process_parser.add_argument("--all", action="store_true", help="Process all pending technologies")
    process_parser.add_argument("--technology", "-t", help="Process specific technology")

    # Status command
    subparsers.add_parser("status", help="Show system status")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query specifications")
    query_parser.add_argument("technology", help="Technology name")
    query_parser.add_argument("--component", "-c", help="Specific component to search for")

    # List command
    subparsers.add_parser("list", help="List registered technologies")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = TechKnowledgeCLI()
    success = False

    try:
        if args.command == "process":
            if args.all:
                success = await cli.process_all()
            elif args.technology:
                success = await cli.process_technology(args.technology)
            else:
                print("❌ Specify --all or --technology <name>")

        elif args.command == "status":
            success = await cli.show_status()

        elif args.command == "query":
            success = await cli.query_specifications(args.technology, args.component)

        elif args.command == "list":
            success = await cli.list_technologies()

    except Exception as e:
        print(f"❌ CLI error: {e}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())