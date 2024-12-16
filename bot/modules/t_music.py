from interactions import *
from interactions.api.events import VoiceStateUpdate
from music.music import *
class NotMusic(Extension):
    
    @listen(VoiceStateUpdate)
    async def event(self, event: VoiceStateUpdate):
        print(event.before)
        print(event.after)
        pass
    
    @slash_command()
    @slash_option('t', 'test', OptionType.STRING, required=True)
    async def music_test(self, ctx: SlashContext, t: str):
        
        await ctx.defer()
        
        await ctx.send('downloading track')
        
        await add_search(t, ctx)
        
        wtf_is_going_on = get_queue(ctx)[0]
        
        if wtf_is_going_on.error == TrackError.PROCESSING:
            return await ctx.send('you fucked up man im sorry')
        
        await ctx.send(f'found **{wtf_is_going_on.title}**')
        
        if not ctx.voice_state:
            await ctx.author.voice.channel.connect()
        
        # ???
        await play_track(self, ctx)
        
        await ctx.send('Finished downloading track :)')