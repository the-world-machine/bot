from interactions import *
from utilities.message_decorations import *
from data.emojis import *
from data.localization import Localization

class InteractModule(Extension):
    
    async def open_interactions_select(self, locale: str, user: User):
        option_list = []
        
        localization = Localization(locale)
        
        interactions: dict[str, dict[str, str]] = localization.l('interact.options')
        
        user_mention = user.mention
        
        for id_, interaction in interactions.items():
            option_list.append(
                StringSelectOption(
                    label=interaction['name'],
                    value=f'{id_}_{user_mention}'
                )
            )
        
        return StringSelectMenu(
            *option_list,
            placeholder=localization.l('interact.placeholder'),
            custom_id='interaction_selected'
        )

    @slash_command()
    @slash_option(name='who', description='The users you want to do the action towards.', opt_type=OptionType.USER)
    async def interaction(self, ctx: SlashContext, who: User):
        '''Interact with other users in various ways.'''
        
        await self.start_interaction(ctx, who)
        
    @user_context_menu('💡 Interact...')
    async def interaction_context(self, ctx: ContextMenuContext):
        
        await self.start_interaction(ctx, ctx.target)
    
    async def start_interaction(self, ctx: SlashContext, who: User):
        
        loc = Localization(ctx.locale)

        if ctx.author.id == who.id:
            return await fancy_message(ctx, loc.l('interact.twm_is_fed_up_with_you', user=ctx.author.mention), ephemeral=True, color=0XFF0000)
        
        if who.id == self.bot.user.id:
            return await fancy_message(ctx, loc.l('interact.twm_not_being_very_happy', user=ctx.author.mention), ephemeral=True, color=0XFF0000)
        
        """if who.bot:
            await fancy_message(ctx, loc.l('interact.twm_questioning_if_youre_stupid_or_not', bot=who.mention, user=ctx.author.mention), ephemeral=True, color=0XFF0000)
            return"""
        
        menu = await self.open_interactions_select(ctx.locale, who)
        
        await ctx.send(content=loc.l('interact.selected', user=who.mention), components=menu, ephemeral=True)
    
    @component_callback('interaction_selected')
    async def menu_callback(self, ctx: ComponentContext):
        
        await ctx.defer(edit_origin=True)
        
        result = ctx.values[0].split('_')
        
        interaction = result[0]
        user = result[1]
        
        localization = Localization(ctx.locale)
               
        await ctx.channel.send(localization.l(f'interact.options.{interaction}.action', user_one=user, user_two=ctx.author.mention))