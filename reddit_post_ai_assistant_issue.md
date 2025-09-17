# When AI Coding Assistants Add Phantom Dependencies: A Claude Story

## r/programming or r/artificial

Just had an interesting experience with Claude that highlights a common AI coding issue - adding unnecessary dependencies.

### The Issue
Claude generated a bash script with this "helpful" prerequisite check:

```bash
python3 -c "import anthropic" 2>/dev/null || {
    print_error "anthropic package not installed. Install with: pip install anthropic"
    exit 1
}
```

Script failed with: `ERROR: anthropic package not installed`

### The Plot Twist
**None of my Python scripts actually import or use the anthropic library.** The actual dependencies were just `whisper`, `requests`, and standard library modules.

### What Happened
Claude (made by Anthropic) assumed its own API library would be used for text summarization, even though the code used different approaches. It created its own roadblock!

### The Lesson
- Always review AI-generated dependency checks  
- Question why each dependency is needed
- Trace through actual imports vs. assumed requirements

### The Fix
Simply removed the phantom check - script works perfectly.

**TL;DR**: AI assistant added a mandatory check for its own company's library that wasn't actually used anywhere in the code. Always verify your dependencies!

---

Has anyone else experienced AI assistants adding phantom dependencies? How do you handle AI code review?

#AI #CodingAssistants #Programming #Dependencies