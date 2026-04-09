#!/usr/bin/env python3
"""
QUICK START GUIDE — Using the OSIRIS Chat System
=================================================

Examples and demonstrations of using OSIRIS v6.0.

Run this script to see examples of:
1. Intent processing
2. Hotkey generation
3. Input detection
4. Agent task execution
5. Mentor protocol in action
6. Agile orchestration
"""

import asyncio
import sys
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).parent.resolve()
SDK_PATH = SCRIPT_DIR / "copilot-sdk-dnalang" / "src"

if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from dnalang_sdk.chat_system import (
    create_intent_processor,
    create_hotkey_engine,
    create_input_processor,
    create_agent_swarm,
    create_mentor_protocol,
    create_agile_orchestrator,
)


def example_1_intent_processing():
    """Example 1: Natural language intent processing"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Intent Processing — Understanding User Goals")
    print("="*80)
    
    processor = create_intent_processor()
    
    # Example inputs
    inputs = [
        "Build a quantum circuit that demonstrates superposition",
        "Debug this error log I got earlier",
        "Help me understand how machine learning works",
        "Create a task management system for my team",
    ]
    
    for user_input in inputs:
        print(f"\n👤 User: '{user_input}'")
        intent = processor.process(user_input)
        
        print(f"🎯 Goal: {intent.primary_goal}")
        print(f"📊 Domains: {', '.join(intent.domains)}")
        print(f"📈 Trajectory: {intent.trajectory}")
        print(f"💪 Confidence: {intent.confidence:.0%}")
        print(f"📋 Actions: {[a.action for a in intent.actions]}")
        print(f"→ Next: {intent.suggested_next_steps[0] if intent.suggested_next_steps else 'None'}")


def example_2_hotkey_generation():
    """Example 2: Context-aware hotkey generation"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Hotkey Engine — Context-Aware Actions")
    print("="*80)
    
    engine = create_hotkey_engine(max_hotkeys=8)
    
    # Generate hotkeys for different scenarios
    scenarios = [
        ("create", ["Design architecture", "Start implementation"], "discovery"),
        ("debug", ["Analyze error", "Fix issue"], "troubleshooting"),
        ("optimize", ["Profile code", "Refactor"], "optimization"),
    ]
    
    for goal, actions, trajectory in scenarios:
        print(f"\n🎯 Goal: {goal.title()} | Trajectory: {trajectory.title()}")
        hotkeys = engine.generate_hotkeys(goal, actions, trajectory)
        
        print(engine.render_hotkeys(hotkeys, width=80))


def example_3_input_detection():
    """Example 3: Universal input processor"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Input Detection — Detecting Any Data Type")
    print("="*80)
    
    processor = create_input_processor()
    
    test_inputs = {
        "Python Code": """def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[0]
    left = [x for x in arr[1:] if x < pivot]
    right = [x for x in arr[1:] if x >= pivot]
    return quick_sort(left) + [pivot] + quick_sort(right)""",
        
        "JSON Data": '{"users": 1024, "active": 856, "metrics": {"engagement": 0.89}}',
        
        "Error Log": """Traceback (most recent call last):
  File "main.py", line 42, in process
    result = quantum_circuit.execute()
IndexError: queue index out of range""",
        
        "Natural Language": "I want to create a system that automatically detects fraudulent transactions",
    }
    
    for label, content in test_inputs.items():
        print(f"\n📝 Input: {label}")
        detected = processor.process(content)
        print(f"   Type: {detected.detected_type.value}")
        print(f"   Language: {detected.language}")
        print(f"   Confidence: {detected.confidence:.0%}")
        print(f"   Summary: {processor.summarize(detected)}")


def example_4_agent_swarm():
    """Example 4: Agent swarm execution"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Agent Swarm — Parallel Multi-Agent Execution")
    print("="*80)
    
    from dnalang_sdk.chat_system.agent_swarm import AgentTask
    
    swarm = create_agent_swarm(max_agents=6)
    
    tasks = [
        AgentTask("task-1", "Analyze requirements", "development"),
        AgentTask("task-2", "Research similar solutions", "research"),
        AgentTask("task-3", "Design architecture", "development"),
    ]
    
    print("\n📤 Spawning tasks...")
    for task in tasks:
        swarm.assign_task(task)
    
    print("⚡ Executing in parallel...")
    
    # Run async code
    async def run_swarm():
        return await swarm.work()
    
    reports = asyncio.run(run_swarm())
    
    print(f"\n✓ Completed {len(reports)} tasks")
    synthesis = swarm.synthesize_findings()
    print(f"📊 Success Rate: {synthesis['success_rate']:.0%}")
    print(f"🤖 Agents: {swarm.get_swarm_status()['active_agents']} active")


def example_5_mentor_protocol():
    """Example 5: Mentor protocol and teaching"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Mentor Protocol — Teaching While Building")
    print("="*80)
    
    from dnalang_sdk.chat_system.mentor_protocol import CapabilityLevel
    
    mentor = create_mentor_protocol()
    
    # Create explanations for different levels
    concepts = ["recursion", "quantum_superposition", "async_await"]
    levels = [CapabilityLevel.NOVICE, CapabilityLevel.INTERMEDIATE, CapabilityLevel.ADVANCED]
    
    concept = "recursion"
    for level in levels:
        print(f"\n📚 Explaining '{concept}' to {level.name} level:")
        explanation = mentor.create_explanation(concept, concept, level)
        print(f"   {explanation.to_text()}")
        if explanation.examples:
            print(f"   Examples: {explanation.examples[0]}")


def example_6_agile_orchestration():
    """Example 6: Agile project management"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Agile Orchestrator — Project Management")
    print("="*80)
    
    agile = create_agile_orchestrator()
    
    # Create a project goal and decompose
    goal = "Build a quantum machine learning system"
    subgoals = [
        "Design quantum feature map",
        "Implement feature encoding",
        "Create optimization routine",
        "Test on simulators",
        "Validate on real hardware",
        "Write documentation",
    ]
    
    print(f"\n🎯 Goal: {goal}")
    print(f"📋 Decomposing into {len(subgoals)} tasks...")
    
    tasks = agile.decompose_goal_into_tasks(goal, subgoals)
    
    # Create sprint
    sprint = agile.create_sprint("sprint-1", "MVP", goal, duration_days=14)
    
    # Plan sprint
    selected = agile.plan_sprint("sprint-1", available_velocity=20)
    
    print(f"\n✓ Sprint Created: {sprint.name}")
    print(f"  Duration: {sprint.duration_days()} days")
    print(f"  Planned Tasks: {len(selected)}")
    
    # Mark some tasks as done
    for task in selected[:2]:
        agile.complete_task(task.task_id)
    
    summary = agile.get_sprint_summary("sprint-1")
    print(f"\n📊 Sprint Status:")
    print(f"  Progress: {summary['progress']:.0%}")
    print(f"  Completed: {summary['completed_points']} / {summary['total_points']} points")
    
    print("\n📋 Daily Standup:")
    print(agile.generate_standup_report())


def main():
    """Run all examples"""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║      OSIRIS v6.0 CHAT SYSTEM — QUICK START EXAMPLES                         ║")
    print("║      Demonstrating intelligent, chat-first interface                        ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    try:
        example_1_intent_processing()
        example_2_hotkey_generation()
        example_3_input_detection()
        example_4_agent_swarm()
        example_5_mentor_protocol()
        example_6_agile_orchestration()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "="*80)
    print("✓ Examples Complete!")
    print("="*80)
    print("\n🎮 To launch interactive chat, run:")
    print("   python osiris_chat.py")
    print("\nType [?] in chat for help, [q] to quit.\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
