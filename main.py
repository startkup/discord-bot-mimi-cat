import interactions, os, firebase_admin, logging
from firebase_admin import credentials, firestore

# These are basic inits for discord bot to function corrrectly
bot = interactions.Client(
    token = os.getenv("DISCORD_TOKEN"),
    default_scope = os.getenv("DISCORD_SCOPE"),
)
bot.load("interactions.ext.persistence")
from interactions.ext.persistence import keygen
keygen()
from interactions.utils.get import get

# These are basic inits for firestore
cred = credentials.Certificate("credentials.json") # <-Not for public
firebase_admin.initialize_app(cred)
db = firestore.client()

# These are basic inits for logging
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)
#------------------------Helper Functions------------------------
def check_df(collection, name):
    doc_ref = db.collection(collection).document(name)
    return doc_ref

def id_to_name(discord_id, collection:str):
    try:
        entry = check_df(collection, discord_id).get()
        if entry.exists :
            return entry.to_dict()['name']
    except:
        print("Somethings wrong with id_to_name")

def validate_date(date_text):
    try:
        return dt.strptime(f'{date_text}', '%Y-%m-%d').date()
    except:
        return False
#----------------------Main Code Starts Here----------------------
name = interactions.TextInput(
    style=interactions.TextStyleType.SHORT,
    label="姓名：",
    custom_id="name_input"
)
studentid = interactions.TextInput(
    style=interactions.TextStyleType.SHORT,
    label="學號：",
    custom_id="studentid_input",
    min_length=6,
    max_length=9,
)

@bot.command(
    name="verify",
    description="自助領取社員身分組",
)
async def verify(ctx):
    modal = interactions.Modal(
        title="社員身分組自助認證",
        custom_id="verify_modal",
        components=[name, studentid]
    )

    await ctx.popup(modal)

@bot.modal("verify_modal")
async def modal_response(ctx, name: str, student_id: int):
    discord_id = f'{ctx.author.username}#{ctx.author.discriminator}'
    logging.info(f"Discord Account: {discord_id} | Name: {name} | StudentID: {student_id}")
    
    ####### 尚未完成將Document ID換成Discord ID的自動取得身分組功能！
    doc_ref = check_df(u"1111-member", name)
    entry = doc_ref.get()
    record = entry.to_dict()
    # Authentication logic(check if name and student ID matches the record in database)
    try:
        if entry.exists and record['student_id'] == student_id:
            await ctx.send(f"✅社員核對通過，請稍後...", ephemeral=True)
            #Replace Database Record with Discord_ID as Key
            db.collection('1111-cadre').document(discord_id).set({
                u'name': name,
                u'student_id': student_id
            })
            doc_ref.delete()
            logging.info(f" - Successfully Updated Discord Account for {name}")
            # Gets role ID
            roles, = interactions.search_iterable(ctx.guild.roles, name='第2屆社員 2nd Gen. Club Member')
            # Add role to user
            await ctx.author.add_role(roles.id)
            logging.info(f" - Successfully Added Role to {name}")
            # Confirm
            await ctx.channel.send(f"{name}您好，已將您加入 `第2屆社員 2nd Gen. Club Member` 身分組！")
        else:
            # In case cadre needs to add member role
            doc_ref = check_df(u"1111-cadre", name)
            entry = doc_ref.get()
            record = entry.to_dict()
            if entry.exists and record['student_id'] == student_id:
                # Add the user's discord account name into the database
                doc_ref.update({
                    u'discord_id': f'{ctx.author.username}#{ctx.author.discriminator}'
                })
                await ctx.send(f"已將您的Discord帳號登錄至資料庫，謝謝！", ephemeral=True)
                logging.info(" - Successfully Update Discord Account for {name}")
                return
    except:
        await ctx.send(f"驗證有誤，請確認姓名及學號是否正確。如有疑問，請透過 <#1024724411074498591> 頻道回報問題，謝謝！", ephemeral=True)

#----------------------幹部----------------------
@bot.command()
async def eip(ctx: interactions.CommandContext):
    """【幹部專用】社團資訊入口 - Club Information Portal"""
    pass

event_dict = {
    "例會": "meeting",
    "社課": "event",
    "檢討會": "AAR",
    "專案": "side-project"
}

#-----------請假-----------
@eip.subcommand()
async def leave(ctx):
    """請假"""
    leave_menu = interactions.SelectMenu(
        custom_id="leave_menu",
        options=[
            interactions.SelectOption(label="例會", value="例會"),
            interactions.SelectOption(label="社課", value="社課"),
            interactions.SelectOption(label="檢討會", value="檢討會"),
            interactions.SelectOption(label="專案", value="專案"),
        ],
    )
    discord_id = f'{ctx.author.username}#{ctx.author.discriminator}'
    entry = check_df(u"1111-cadre", discord_id).get()
    if entry.exists:
        await ctx.send("請選擇欲請假的活動類型", components=leave_menu)
    else:
        await ctx.send(":warning: 這個功能僅限現任幹部使用", ephemeral=True)

@bot.component("leave_menu")
async def callback(ctx, response: str):
    event_selection, *_ = response
    custom_id = interactions.ext.persistence.PersistentCustomID(
        bot,
        "leave_form",
        event_dict[event_selection], # Persistence extension will crash when encountering Chinese, [see here](https://discord.com/channels/789032594456576001/1037090379935256576/1037386313592229928)
    )
    modal = interactions.Modal(
        title=f"【{event_selection}】請假單",
        components=[
            interactions.TextInput(
                style=interactions.TextStyleType.SHORT,
                label="請假時間（YYYY-MM-DD）",
                custom_id="leave_date",
                min_length=10,
                max_length=10
            ),
            interactions.TextInput(
                style=interactions.TextStyleType.SHORT,
                label="請假類別（按學校分類）",
                custom_id="leave_type",
            ),
            interactions.TextInput(
                style=interactions.TextStyleType.PARAGRAPH,
                label="請假原因",
                custom_id="leave_reason"
            )
            # type: ignore
        ],
        custom_id = str(custom_id)
    )
    await ctx.popup(modal)
    await ctx.message.delete()

@bot.persistent_modal("leave_form")
async def modal_response(ctx, event_type, leave_date: str, leave_type: str, leave_reason: str):
    leave_date = validate_date(leave_date)
    if leave_date:
        leave_delta = (leave_date - dt.today().date()).days
        if leave_delta > 0: #確保不可在當天或逾期請假
            channel = await get(bot, interactions.Channel, object_id=env.leave_channel)
            discord_id = f'{ctx.author.username}#{ctx.author.discriminator}'
            timestamp = dt.now().isoformat()
            leave_name = list(event_dict.keys())[list(event_dict.values()).index(event_type)]
            # logging.info(f"Leave =>")
            embeds=interactions.Embed(title=f"【{leave_name}】請假單", color=0x00bfff)
            embeds.set_author(name=f"{id_to_name(discord_id, '1111-cadre')}", icon_url=f"{ctx.author.avatar_url}?size=1024")
            embeds.set_thumbnail(url="https://i.ibb.co/6BK3PR9/image.png")
            embeds.add_field(name="假別", value=f"{leave_type}\a\a\a\a", inline=True)
            embeds.add_field(name="時間", value=f"{leave_date}", inline=True)
            embeds.add_field(name="請假原因", value=f"{leave_reason}", inline=False)
            embeds.set_footer(text=f"假單序號：{timestamp}")
            result = await channel.send(embeds=embeds)
            btn_custom_id = interactions.ext.persistence.PersistentCustomID(
                bot,
                "btn_revoke_leave",
                [str(result.id), timestamp],
            )

            db.collection(u'1111-leave').document(timestamp).set({
                u'date': timestamp,
                u'name': discord_id,
                u'type': leave_type,
                u'reason': leave_reason
            })
            db.collection(u'1111-cadre').document(discord_id).update({
                u'leave_record': firestore.ArrayUnion([timestamp])
            })

            button = interactions.Button(
                style = interactions.ButtonStyle.DANGER,
                label = "↻ 撤回",
                custom_id = str(btn_custom_id)  
            )
            await ctx.send("", components=button)
        else:
            await ctx.send("請假不可於當天/逾期請！\n如有急事非請不可，請在 <#1022436666251677737> 表示請假原因。", ephemeral=True)
    else:
        await ctx.send("時間格式不正確，請確認是否為 `MM/DD`", ephemeral=True)

@bot.persistent_component("btn_revoke_leave")
async def button_response(ctx, payload: list):
    btn_custom_id, timestamp = payload
    discord_id = f'{ctx.author.username}#{ctx.author.discriminator}'
    db.collection(u'1111-leave').document(timestamp).delete()
    db.collection(u'1111-cadre').document(discord_id).update({
        u'leave_record': firestore.ArrayRemove([timestamp])
    })
    await ctx.message.edit(f"已撤回假單")
    message = await get(bot, interactions.Message, object_id=btn_custom_id)
    await message.delete()

#-----------公告-----------
announcement_dict = {
    "活動公告": "event",
    "會議通知": "meeting"
}

@eip.subcommand()
async def announcement(ctx):
    """公告"""
    announcement_menu = interactions.SelectMenu(
        custom_id="announcement_menu",
        options=[
            interactions.SelectOption(label="活動公告", value="活動公告"),
            interactions.SelectOption(label="會議通知", value="會議通知"),
        ],
    )
    discord_id = f'{ctx.author.username}#{ctx.author.discriminator}'
    entry = check_df(u"1111-cadre", discord_id).get()
    if entry.exists:
        await ctx.send("請選擇欲公告類型", components=announcement_menu)
    else:
        await ctx.send(":warning: 這個功能僅限現任幹部使用", ephemeral=True)

@bot.component("announcement_menu")
async def callback(ctx, response: str):
    announcement_selection, *_ = response
    custom_id = interactions.ext.persistence.PersistentCustomID(
        bot,
        "announcement_form",
        announcement_dict[announcement_selection],
    )
    modal = interactions.Modal(
        title=f"【{announcement_selection}】",
        components=[
            interactions.TextInput(
                style=interactions.TextStyleType.SHORT,
                label="標題",
                custom_id="announcement_title"
            ),
            interactions.TextInput(
                style=interactions.TextStyleType.SHORT,
                label="對象（選填）",
                custom_id="announcement_target",
                required=False
            ),
            interactions.TextInput(
                style=interactions.TextStyleType.SHORT,
                label="日期 YYYY-MM-DD（選填）",
                custom_id="announcement_date",
                required=False
            ),
            interactions.TextInput(
                style=interactions.TextStyleType.PARAGRAPH,
                label="內容",
                custom_id="announcement_content"
            )
            # type: ignore
        ],
        custom_id = str(custom_id)
    )
    await ctx.popup(modal)
    await ctx.message.delete()

@bot.persistent_modal("announcement_form")
async def modal_response(ctx, announcement_type, announcement_title: str, announcement_target: str, announcement_date:str, announcement_content: str):
    if announcement_date:
        announcement_date = validate_date(announcement_date)
        if not announcement_date:
            await ctx.send("日期格式不正確，請確認是否為 `YYYY-MM-DD`", ephemeral=True)
            return
    if announcement_target:
        roles = interactions.search_iterable(ctx.guild.roles, name=announcement_target)
        if not roles:
            await ctx.send("標記身分組不正確，請再次核對名稱。", ephemeral=True)
            return
        else:
            role, = roles # Unpack from list
    channel = await get(bot, interactions.Channel, object_id=<announcement_channel>) # Replace <announcement_channel> with the actual announcement channel ID
    name = list(announcement_dict.keys())[list(announcement_dict.values()).index(announcement_type)]
    msg = f"【{name}】\n" +\
        f"標題：{announcement_title}\n" +\
        (f"對象：{role.mention}\n" if announcement_target else "") +\
        (f"日期：{announcement_date}\n" if announcement_date else "") +\
        f"內容：{announcement_content}"
    await channel.send(msg)
    await ctx.send("已發公告")
    await ctx.message.delete()

bot.start()
