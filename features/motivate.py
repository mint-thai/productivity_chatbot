"""
Motivational nudges system for Kairos productivity chatbot.
Provides encouragement, productivity tips, and motivational quotes.
"""

import random

# Curated motivational quotes focused on growth, career, and overcoming adversity
MOTIVATIONAL_QUOTES = [
    # Growth & Learning
    "The only way to do great work is to love what you do. — Steve Jobs",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. — Winston Churchill",
    "Your time is limited, don't waste it living someone else's life. — Steve Jobs",
    "The expert in anything was once a beginner. — Helen Hayes",
    "Don't watch the clock; do what it does. Keep going. — Sam Levenson",
    "The future depends on what you do today. — Mahatma Gandhi",
    "Believe you can and you're halfway there. — Theodore Roosevelt",
    
    # Career & Ambition
    "The only impossible journey is the one you never begin. — Tony Robbins",
    "Opportunities don't happen. You create them. — Chris Grosser",
    "Don't be afraid to give up the good to go for the great. — John D. Rockefeller",
    "Success usually comes to those who are too busy to be looking for it. — Henry David Thoreau",
    "The way to get started is to quit talking and begin doing. — Walt Disney",
    "Innovation distinguishes between a leader and a follower. — Steve Jobs",
    "Your work is going to fill a large part of your life, and the only way to be truly satisfied is to do what you believe is great work. — Steve Jobs",
    
    # Overcoming Adversity
    "It does not matter how slowly you go as long as you do not stop. — Confucius",
    "Everything you've ever wanted is on the other side of fear. — George Addair",
    "Hardships often prepare ordinary people for an extraordinary destiny. — C.S. Lewis",
    "The only limit to our realization of tomorrow will be our doubts of today. — Franklin D. Roosevelt",
    "Do not wait; the time will never be 'just right.' Start where you stand. — Napoleon Hill",
    "Fall seven times, stand up eight. — Japanese Proverb",
    "Challenges are what make life interesting; overcoming them is what makes life meaningful. — Joshua Marine",
    "You are never too old to set another goal or to dream a new dream. — C.S. Lewis",
    
    # Productivity & Focus
    "Focus on being productive instead of busy. — Tim Ferriss",
    "The secret of getting ahead is getting started. — Mark Twain",
    "You don't have to be great to start, but you have to start to be great. — Zig Ziglar",
    "Action is the foundational key to all success. — Pablo Picasso",
    "The difference between ordinary and extraordinary is that little extra. — Jimmy Johnson",
    "Small daily improvements over time lead to stunning results. — Robin Sharma",
    
    # Persistence & Resilience
    "I have not failed. I've just found 10,000 ways that won't work. — Thomas Edison",
    "Success is walking from failure to failure with no loss of enthusiasm. — Winston Churchill",
    "The harder you work for something, the greater you'll feel when you achieve it.",
    "Don't stop when you're tired. Stop when you're done.",
    "Your limitation—it's only your imagination.",
    "Great things never come from comfort zones.",
    "Dream it. Wish it. Do it.",
]

# Productivity tips and actionable advice
PRODUCTIVITY_TIPS = [
    "💡 Break large tasks into smaller, manageable chunks. You'll feel accomplished with each step!",
    "⏰ Try the 2-minute rule: If it takes less than 2 minutes, do it now!",
    "🎯 Prioritize your top 3 tasks each morning. Everything else is secondary.",
    "🚫 Turn off notifications during deep work sessions. Your focus will thank you.",
    "☕ Take regular breaks. Your brain needs rest to stay productive.",
    "📝 Write down tomorrow's tasks before bed. Wake up with clarity and purpose.",
    "🔄 Review your progress weekly. Celebrate wins and adjust your strategy.",
    "🧘 Start your day with 5 minutes of mindfulness. Mental clarity leads to better decisions.",
    "📱 Batch similar tasks together. Context switching kills productivity.",
    "✅ Done is better than perfect. Progress over perfection, always.",
    "🎧 Use music or white noise to create your ideal focus environment.",
    "🌅 Tackle your hardest task first thing in the morning when your energy is highest.",
    "📊 Track your time for a week. You'll be surprised where it goes.",
    "🎪 Create a dedicated workspace. Your environment shapes your mindset.",
    "🔋 Protect your energy like your phone battery. Say no to drains.",
]

# Encouragement messages for different scenarios
ENCOURAGEMENT_MESSAGES = {
    "morning": [
        "☀️ Good morning! Today is full of possibilities. Let's make it count!",
        "🌅 Rise and shine! Your future self will thank you for the work you do today.",
        "💪 New day, fresh start. You've got this!",
        "🎯 Today's goal: Progress, not perfection. Let's go!",
    ],
    "evening": [
        "🌙 Great work today! Remember to rest—tomorrow is another opportunity to shine.",
        "✨ You showed up today. That's what matters. Rest well!",
        "🏆 Another day of progress. Celebrate your wins, no matter how small.",
        "😌 Time to recharge. You've earned it!",
    ],
    "struggling": [
        "💪 Struggling is part of growth. Keep pushing—you're stronger than you think!",
        "🌱 Every expert was once where you are. Keep learning, keep growing.",
        "🔥 Challenges are just opportunities in disguise. You've got this!",
        "⭐ Remember why you started. That fire is still in you!",
    ],
    "productive": [
        "🚀 You're on fire! This momentum is incredible—keep it going!",
        "🏅 Look at you crushing those goals! This is the energy!",
        "⚡ This is what peak performance looks like. You're amazing!",
        "🎉 Productivity level: Expert! Keep riding this wave!",
    ],
}


def get_random_quote():
    """Get a random motivational quote."""
    return random.choice(MOTIVATIONAL_QUOTES)


def get_random_tip():
    """Get a random productivity tip."""
    return random.choice(PRODUCTIVITY_TIPS)


def get_encouragement(scenario="morning"):
    """
    Get an encouragement message for a specific scenario.
    
    Args:
        scenario: One of 'morning', 'evening', 'struggling', 'productive'
    
    Returns:
        str: Encouragement message
    """
    messages = ENCOURAGEMENT_MESSAGES.get(scenario, ENCOURAGEMENT_MESSAGES["morning"])
    return random.choice(messages)


def get_nudge_message(include_tip=False):
    """
    Generate a complete nudge message with quote and optional tip.
    
    Args:
        include_tip: Whether to include a productivity tip (default: False, quote only)
    
    Returns:
        str: Complete nudge message
    """
    quote = get_random_quote()
    
    if include_tip:
        tip = get_random_tip()
        return f"✨ {quote}\n\n{tip}"
    
    return f"✨ {quote}"


def get_email_footer_nudge():
    """
    Get a motivational message suitable for email footers.
    Shorter and more focused than full nudges.
    
    Returns:
        str: HTML formatted motivational message
    """
    quote = get_random_quote()
    
    html = f"""
    <div style="margin-top: 30px; padding: 20px; background-color: #f0f7ff; border-left: 4px solid #4A90E2; border-radius: 4px;">
        <p style="margin: 0; font-style: italic; color: #555;">
            "{quote}"
        </p>
    </div>
    """
    
    return html
