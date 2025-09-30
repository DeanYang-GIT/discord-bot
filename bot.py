import discord
from discord.ext import commands, tasks
import re
import asyncio
from datetime import datetime, timedelta
import os
from collections import defaultdict

# Bot configuration
TOKEN = os.getenv('MTQyMjcwODQ5NjE4MDMxNDIxMg.GO1xgO.-BwIbmCArTM__TWr3MxijPW8X9K6xMp2-fit_A')  # Set this in your environment
MESSAGE_TRACKING_LIMIT = 10  # Track first 10 messages per user
AUTO_DELETE_DELAY = 600  # 10 minutes in seconds

class AskToAskBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)
        
        # Track message counts for new users
        self.user_message_counts = defaultdict(int)
        
        # Store messages to delete later
        self.messages_to_delete = []
        
        # Ask-to-ask patterns (can be expanded based on real examples)
        self.ata_patterns = [
            # Classic ask-to-ask patterns
            r'^can\s+(i|someone|anyone)\s+(ask|get\s+help).*\?*$',
            r'^(is\s+)?(anyone|someone)\s+(here|available|around).*\?*$',
            r'^(can|may)\s+i\s+ask\s+.*question.*\?*$',
            r'^(does\s+)?(anyone|someone)\s+know\s+about.*\?*$',
            r'^(is\s+it\s+ok|okay)\s+(to|if\s+i)\s+ask.*\?*$',
            r'^(i\s+)?need\s+help\s+with\s+\w+(\s+\w+)?$',
            r'^quick\s+question.*$',
            r'^(hey|hi|hello).*can\s+(someone|anyone)\s+help.*\?*$',
            r'^anyone\s+(good|expert)\s+(with|at|in).*\?*$',
            r'^who\s+(can|could)\s+help\s+(me\s+)?(with|on).*\?*$',
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.ata_patterns]
    
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        self.cleanup_old_messages.start()
    
    def is_ask_to_ask(self, message_content):
        """Check if a message matches ask-to-ask patterns"""
        # Clean the message
        clean_msg = message_content.strip()
        
        # Check basic heuristics
        word_count = len(clean_msg.split())
        if word_count < 3 or word_count > 12:
            return False
        
        # Check against patterns
        for pattern in self.compiled_patterns:
            if pattern.match(clean_msg):
                return True
        
        # Additional heuristic: Check for subject-specific terms ratio
        common_words = {'can', 'i', 'ask', 'a', 'question', 'anyone', 'someone', 
                       'help', 'here', 'with', 'about', 'need', 'please', 'thanks',
                       'hey', 'hi', 'hello', 'is', 'it', 'ok', 'okay', 'to', 'if',
                       'there', 'who', 'could', 'me', 'on', 'for', 'quick', 'got',
                       'have', 'does', 'know', 'good', 'at', 'in', 'expert'}
        
        words = clean_msg.lower().split()
        non_common_count = sum(1 for word in words if word.strip('?.,!') not in common_words)
        
        # If message has mostly common words and ends with ? or contains help/question
        if non_common_count <= 2 and ('?' in clean_msg or 
                                       any(word in clean_msg.lower() for word in ['help', 'question', 'ask'])):
            return True
        
        return False
    
    def generate_help_message(self):
        """Generate the helpful guide message"""
        return """
**📚 How to Ask Great Questions in Our Community**

Hey there! It looks like you might be new here. No worries - we're happy to help! Here's a quick guide on getting the best help possible:

**✅ Good Question Examples:**

**When stuck on a specific problem:**
> "I'm trying to solve this integral ∫x²sin(x)dx using integration by parts, but I keep getting a different answer than the textbook. Here's my work: [show steps]. Where am I going wrong?"

**When struggling with a concept:**
> "I don't understand how eigenvectors work. I know they're vectors that don't change direction when a matrix is applied, but what does that actually mean practically? Can someone explain with a simple 2x2 example?"

**When looking for resources:**
> "I want to learn machine learning basics. My math background is calculus and basic linear algebra. What resources would you recommend for someone at my level?"

**❌ Instead of asking these:**
- "Can anyone help me with calculus?"
- "Is anyone here good at programming?"
- "Quick question about linear algebra"
- "Can I ask something?"

**Just ask these directly:**
- "How do I find the derivative of x³ln(x)?"
- "Why is my Python loop giving an IndexError on line 5? [paste code]"
- "What's the difference between rank and nullity of a matrix?"
- "Does anyone have book recommendations for learning abstract algebra?"

**💡 Pro tip:** The more specific you are, the faster and better help you'll get! Include what you've tried, where you're stuck, or what confuses you.

*This message will auto-delete in 10 minutes to keep the chat clean!*"""
    
    async def on_message(self, message):
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Process commands first
        await self.process_commands(message)
        
        # Only check for ask-to-ask in the first N messages from a user
        if self.user_message_counts[message.author.id] < MESSAGE_TRACKING_LIMIT:
            self.user_message_counts[message.author.id] += 1
            
            if self.is_ask_to_ask(message.content):
                await self.send_help_guide(message)
    
    async def send_help_guide(self, trigger_message):
        """Send the help guide and schedule deletion"""
        guide = self.generate_help_message()
        
        # Send the guide as a reply
        response = await trigger_message.reply(guide)
        
        # Schedule both messages for deletion
        delete_time = datetime.now() + timedelta(seconds=AUTO_DELETE_DELAY)
        self.messages_to_delete.append({
            'messages': [trigger_message, response],
            'delete_time': delete_time
        })
    
    @tasks.loop(seconds=30)
    async def cleanup_old_messages(self):
        """Periodically clean up old messages"""
        now = datetime.now()
        messages_to_remove = []
        
        for entry in self.messages_to_delete:
            if now >= entry['delete_time']:
                for msg in entry['messages']:
                    try:
                        await msg.delete()
                    except discord.NotFound:
                        pass  # Message already deleted
                    except discord.Forbidden:
                        pass  # No permission to delete
                messages_to_remove.append(entry)
        
        # Remove deleted entries
        for entry in messages_to_remove:
            self.messages_to_delete.remove(entry)
    
    @cleanup_old_messages.before_loop
    async def before_cleanup(self):
        await self.wait_until_ready()

# Create bot instance
bot = AskToAskBot()

@bot.command(name='q', help='Manually trigger the ask-to-ask guide')
async def manual_guide(ctx):
    """Manual trigger command for the guide"""
    guide = bot.generate_help_message()
    response = await ctx.send(guide)
    
    # Schedule for deletion
    delete_time = datetime.now() + timedelta(seconds=AUTO_DELETE_DELAY)
    bot.messages_to_delete.append({
        'messages': [ctx.message, response],
        'delete_time': delete_time
    })

@bot.command(name='ata_stats', help='Show ask-to-ask detection stats (admin only)')
@commands.has_permissions(administrator=True)
async def show_stats(ctx):
    """Show statistics about message tracking"""
    total_tracked = len(bot.user_message_counts)
    pending_deletions = len(bot.messages_to_delete)
    
    embed = discord.Embed(
        title="Ask-to-Ask Bot Statistics",
        color=discord.Color.blue()
    )
    embed.add_field(name="Users being tracked", value=total_tracked, inline=True)
    embed.add_field(name="Pending message deletions", value=pending_deletions, inline=True)
    
    await ctx.send(embed=embed, delete_after=30)

@bot.command(name='ata_reset', help='Reset tracking for a user (admin only)')
@commands.has_permissions(administrator=True)
async def reset_user(ctx, member: discord.Member):
    """Reset message count for a specific user"""
    if member.id in bot.user_message_counts:
        bot.user_message_counts[member.id] = 0
        await ctx.send(f"Reset message tracking for {member.mention}", delete_after=10)
    else:
        await ctx.send(f"{member.mention} is not being tracked", delete_after=10)

# Run the bot
if __name__ == "__main__":
    bot.run(TOKEN)