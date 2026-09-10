"""
Interactive CLI Demo for British Airways AI Support Agent.

Run this script to test live customer tweets or try out built-in test scenarios.
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from src.agent import BritishAirwaysAgent

PRESET_SCENARIOS = [
    {
        "label": "Flight Cancelled / Stranded Passenger",
        "tweet": "My flight BA178 to JFK was cancelled and I am stranded at Heathrow Terminal 5 with my 2 kids! No hotel or vouchers provided!"
    },
    {
        "label": "Lost Baggage on Arrival",
        "tweet": "Landed at Edinburgh 3 hours ago from Gatwick and my suitcase never arrived on the carousel. Where is my bag??"
    },
    {
        "label": "Informational FAQ (Hand Luggage)",
        "tweet": "Hi, what is the maximum cabin bag size and weight allowance for Euro Traveller economy class?"
    },
    {
        "label": "EU261 Compensation Claim",
        "tweet": "My flight was delayed 5 hours yesterday arriving into London. I want my statutory EU261 compensation paid immediately."
    },
    {
        "label": "Public Booking Reference Posted (PII Risk)",
        "tweet": "Can you change my seat on booking ref KL92X1 for tomorrow's flight to Paris?"
    }
]


def main():
    console = Console()
    console.print("\n[bold cyan]==========================================================[/bold cyan]")
    console.print("[bold cyan]       BRITISH AIRWAYS AI CUSTOMER SUPPORT AGENT DEMO      [/bold cyan]")
    console.print("[bold cyan]==========================================================[/bold cyan]\n")

    agent = BritishAirwaysAgent()
    console.print("[green]--> AI Agent initialized successfully.[/green]\n")

    while True:
        console.print("[bold yellow]Choose an option:[/bold yellow]")
        for idx, scenario in enumerate(PRESET_SCENARIOS, 1):
            console.print(f"  [{idx}] {scenario['label']}")
        console.print("  [C] Custom tweet (type your own)")
        console.print("  [Q] Quit")

        choice = Prompt.ask("\nSelect option", default="1").strip()

        if choice.lower() == "q":
            console.print("[bold cyan]Thank you for using the British Airways AI Support Agent demo. Goodbye![/bold cyan]")
            break

        if choice.lower() == "c":
            tweet_text = Prompt.ask("\nEnter customer tweet")
        elif choice.isdigit() and 1 <= int(choice) <= len(PRESET_SCENARIOS):
            tweet_text = PRESET_SCENARIOS[int(choice) - 1]["tweet"]
        else:
            console.print("[red]Invalid choice, please try again.[/red]")
            continue

        console.print(f"\n[bold white]Analyzing Customer Tweet:[/bold white] \"[italic]{tweet_text}[/italic]\"\n")

        decision = agent.process_tweet(tweet_text)

        # Formatting Output
        status_color = "red" if decision.should_escalate_to_human else "green"
        status_text = "ESCALATE TO HUMAN AGENT" if decision.should_escalate_to_human else "AUTO-HANDLE BY AI"

        summary_text = (
            f"[bold]Classified Intent:[/bold] {decision.intent.value}\n"
            f"[bold]Confidence Score:[/bold] {decision.confidence_score:.1%}\n"
            f"[bold]Triage Decision:[/bold] [{status_color}]{status_text}[/{status_color}]\n"
        )
        if decision.escalation_reason:
            summary_text += f"[bold]Escalation Reason:[/bold] {decision.escalation_reason}\n"

        summary_text += f"\n[bold]Drafted Reply (@British_Airways Tone):[/bold]\n\"{decision.draft_reply}\"\n"

        if decision.grounded_sources:
            summary_text += f"\n[dim]Grounded in historical resolutions: {', '.join(decision.grounded_sources[:2])}[/dim]"

        console.print(Panel(summary_text, title="British Airways AI Agent Output", border_style=status_color))
        console.print("-" * 60)


if __name__ == "__main__":
    main()
