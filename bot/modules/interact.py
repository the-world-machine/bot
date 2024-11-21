import random
from interactions import *
from utilities.message_decorations import *
from utilities.localization import Localization, assign_variables

def make_interactions_select_menu(loc: Localization, uid: User) -> StringSelectMenu:
        option_list = []
        
        interactions: dict[str, dict[str, str]] = loc.l('interact.options')
        
        for id_, interaction in interactions.items():
            option_list.append(
                StringSelectOption(
                    label=interaction['name'],
                    value=f'{id_}_{uid}'
                )
            )
        
        return StringSelectMenu(
            *option_list,
            placeholder=loc.l('interact.placeholder'),
            custom_id='interaction_selected'
        )

class InteractModule(Extension):
    @slash_command()
    @slash_option(name='with', description='The person you want to interact with', opt_type=OptionType.USER, required=True, argument_name="user")
    async def interaction(self, ctx: SlashContext, user: User):
        '''Interact with others in various ways (sends a message in chat).'''
        
        await self.start_interaction(ctx, user)
        
    @user_context_menu('💡 Interact...')
    async def interaction_context(self, ctx: ContextMenuContext):
        
        await self.start_interaction(ctx, ctx.target)
    
    async def start_interaction(self, ctx: SlashContext, who: User):
        
        loc = Localization(ctx)

        if ctx.author.id == who.id:
            return await fancy_message(ctx, loc.l('interact.twm_is_fed_up_with_you', user=ctx.author.mention), ephemeral=True, color=0XFF0000)
        
        if who.id == self.bot.user.id:
            return await fancy_message(ctx, loc.l('interact.twm_not_being_very_happy', user=ctx.author.mention), ephemeral=True, color=0XFF0000)
        
        """if who.bot:
            await fancy_message(ctx, loc.l('interact.twm_questioning_if_youre_stupid_or_not', bot=who.mention, user=ctx.author.mention), ephemeral=True, color=0XFF0000)
            return"""
        
        menu = make_interactions_select_menu(loc, who.id)
        
        await ctx.send(content=loc.l('interact.selected', user=who.mention), components=menu, ephemeral=True)
    
    @component_callback('interaction_selected')
    async def menu_callback(self, ctx: ComponentContext):
        loc = Localization(ctx)
        await ctx.defer(edit_origin=True)
        
        args = ctx.values[0].split('_')
        user = ctx.client.get_user(args[1])
        text = loc.l(f'interact.options.{args[0]}.messages')
        if isinstance(text, list):
            text = random.choice(text)
        
        await ctx.channel.send(assign_variables(text, locale=ctx.locale, user_one=ctx.author.mention, user_two=user.mention))

        await ctx.edit(components=[make_interactions_select_menu(loc, user.id)])