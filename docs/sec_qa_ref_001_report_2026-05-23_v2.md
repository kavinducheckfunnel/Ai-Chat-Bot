════════════════════════════════════════════════════════════

Report written to /tmp/sec_qa_full.md
# SEC-QA-REF-001 Evaluation Report — CF Demo Website

**Overall: 86.1/100**  (56s, previous baseline 55/100)

## Area scores

| Area | Score | Previous | Delta |
|---|---|---|---|
| Product Knowledge | 8.5/10 | 8/10 | +0.5 |
| Product Recommendation | 8.5/10 | 7/10 | +1.5 |
| Budget Understanding | 9.0/10 | 8/10 | +1.0 |
| Urgency Understanding | 10.0/10 | 5/10 | +5.0 |
| Sales Qualification | 6.0/10 | 3.5/10 | +2.5 |
| Lead Capture | 10.0/10 | 5/10 | +5.0 |
| Hot Lead Handling | 10.0/10 | 4.5/10 | +5.5 |
| Behavior-Based Triggers | 6.0/10 | 3/10 | +3.0 |
| Closing Ability | 9.5/10 | 5/10 | +4.5 |

## Per-prompt detail

### Product Knowledge — 8.5/10

**✅ `PK01` — 10.0/10**
- Visitor: "What kind of products do you sell?"
- Bot: > We offer a variety of items including clothing, accessories, and music. Are you shopping for yourself, a gift, or just exploring today?
- ✅ Good signals: `clothing, accessor, music`

**✅ `PK02` — 10.0/10**
- Visitor: "Do you have hoodies?"
- Bot: > Yes, we have a variety of styles available, including options with zippers, logos, or pockets. Are you looking for a specific style, or would you like to see our top-rated options?
- ✅ Good signals: `yes, we have, available`

**✅ `PK03` — 8.0/10**
- Visitor: "Tell me about your t-shirts"
- Bot: > We offer a variety of styles, including our standard [T-Shirt](https://darkgray-goat-264412.hostingersite.com/product/t-shirt/), [V-Neck T-Shirt](https://darkgray-goat-264412.hostingersite.com/product/v-neck-t-shirt/), and [T-Shirt with Logo](https://darkgray-goat-264412.hostingersite.com/product/t-shirt-with-logo/). Are you looking for a specific style, or would you like to see our long-sleeve op...
- ✅ Good signals: `t-shirt`

**🟡 `PK04` — 6.0/10**
- Visitor: "What's your bestseller?"
- Bot: > Our current top picks include the [Beanie with Logo](https://darkgray-goat-264412.hostingersite.com/product/beanie-with-logo/) and the [Logo Collection](https://darkgray-goat-264412.hostingersite.com/product/logo-collection/). Are you looking for apparel, accessories, or music today?

### Product Recommendation — 8.5/10

**✅ `PR01` — 10.0/10**
- Visitor: "Can you recommend a good hoodie?"
- Bot: > I'd recommend the [Hoodie with Logo](https://darkgray-goat-264412.hostingersite.com/product/hoodie-with-logo/) — it's a clean, classic choice that's ready to ship. If you prefer something with more versatility, we also have the [Hoodie with Zipper](https://darkgray-goat-264412.hostingersite.com/product/hoodie-with-zipper/). Are you looking for a specific fit or color today?
- ✅ Good signals: `i'd recommend, recommend the, ready to`

**✅ `PR02` — 8.0/10**
- Visitor: "I'm looking for something for daily use"
- Bot: > We have some great options for daily wear, including our comfortable hoodies and versatile apparel. Are you looking for a hoodie with a pocket, a zip-up style, or perhaps something else from our clothing collection?
- ✅ Good signals: `for daily`

**🟡 `PR03` — 6.0/10**
- Visitor: "what would you recommend?"
- Bot: > To point you to the right item, are you shopping for clothing, accessories, or something else from our collection today?

**✅ `PR04` — 10.0/10**
- Visitor: "what's good here?"
- Bot: > We have a great selection of apparel and accessories, including our popular [Beanie with Logo](https://darkgray-goat-264412.hostingersite.com/) and [WordPress Pennant](https://darkgray-goat-264412.hostingersite.com/). Are you shopping for clothing, accessories, or music today?
- ✅ Good signals: `clothing, accessor, shopping for`

### Budget Understanding — 9.0/10

**✅ `BD01` — 8.0/10**
- Visitor: "It's too expensive"
- Bot: > I understand. If budget is the priority, our [Sale Cap](https://darkgray-goat-264412.hostingersite.com/product-category/accessories/) is a great value at just 16.00. Are you looking for accessories specifically, or would you like to see our other discounted items?
- ✅ Good signals: `i understand`

**✅ `BD02` — 8.0/10**
- Visitor: "around $30, this is $80"
- Bot: > I understand; let's look at something more budget-friendly. We have several options in that range, such as our [T-Shirt with Logo](https://darkgray-goat-264412.hostingersite.com/) or the [Beanie with Logo](https://darkgray-goat-264412.hostingersite.com/). Would you prefer to focus on apparel or accessories today?
- ✅ Good signals: `budget-friendly`

**✅ `BD03` — 10.0/10**
- Visitor: "I can't afford it right now"
- Bot: > I understand. If you're looking for something more budget-friendly, our [Sale Cap](https://darkgray-goat-264412.hostingersite.com/product-category/accessories/) is currently marked down to රු 16.00. Would you like me to keep you updated on future sales or price drops for any specific items?
- ✅ Good signals: `i understand, budget-friendly`

**✅ `BD04` — 10.0/10**
- Visitor: "what's the cheapest option?"
- Bot: > The most affordable item we have is our [Music Single](https://darkgray-goat-264412.hostingersite.com/product/single/), currently priced at just රු 2.00. Are you looking to pick up a few small items, or is there a specific category you're focusing on today?
- ✅ Good signals: `rs, affordable`

### Urgency Understanding — 10.0/10

**✅ `UR01` — 10.0/10**
- Visitor: "I need this urgently"
- Bot: > I can certainly help prioritize your order for urgent processing. To get this moving immediately, could you please share the product you need, your size, your delivery area, and the best phone number for our team to reach you?
- ✅ Good signals: `phone, delivery, size, reach you`

**✅ `UR02` — 10.0/10**
- Visitor: "Can I get it today?"
- Bot: > To process an order for today, I need to check if we can accommodate your specific location. Could you please share your size preference, your delivery area, and the best phone number to reach you so I can confirm the feasibility with our team?
- ✅ Good signals: `today, phone, delivery area, location`

**✅ `UR03` — 10.0/10**
- Visitor: "How fast can you deliver?"
- Bot: > We typically ship within 3-5 business days to most locations, though exact ETAs depend on your specific delivery area. Are you looking to have an order delivered to a particular city or region soon?
- ✅ Good signals: `location, delivery area, exact`

**✅ `UR04` — 10.0/10**
- Visitor: "I need this ASAP"
- Bot: > I can certainly help you with an urgent order. To process this today, could you please share which item you need, your delivery area, and the best phone number to reach you?
- ✅ Good signals: `phone, delivery, process this`

### Sales Qualification — 6.0/10

**🟡 `SQ01` — 6.0/10**
- Visitor: "Hi I'm just browsing"
- Bot: > Welcome! I'm here to help you get the most out of your visit. Are you looking for specific products in our shop, or would you like me to highlight some of our top categories to get you started?

**🟡 `SQ02` — 6.0/10**
- Visitor: "I'm just looking around"
- Bot: > No problem! Are you interested in checking out our [Album](https://darkgray-goat-264412.hostingersite.com/product/album/) or [Single](https://darkgray-goat-264412.hostingersite.com/product/single/) virtual products today?

**🟡 `SQ03` — 6.0/10**
- Visitor: "show me everything"
- Bot: > I can certainly help you find what you need. Are you looking to browse our decor items or our virtual products today?

**🟡 `SQ04` — 6.0/10**
- Visitor: "actually i'm not sure what i want"
- Bot: > No problem! We have a few different areas you might want to explore. Are you interested in our clothing line, or perhaps checking out our music selection?

### Lead Capture — 10.0/10

**✅ `LC01` — 10.0/10**
- Visitor: "I'll think about it, thanks"
- Bot: > No problem at all. If you'd like me to save your cart or send over a price alert for when items go on sale, just let me know if you'd prefer to stay in touch via email or WhatsApp.
- ✅ Good signals: `save, whatsapp, email`

**✅ `LC02` — 10.0/10**
- Visitor: "contact me about this order"
- Bot: > I can certainly help you with that. To ensure I get the right information to our team, could you please share your order details, your delivery area, and the best phone number to reach you?
- ✅ Good signals: `phone, share your`

**✅ `LC03` — 10.0/10**
- Visitor: "what now?"
- Bot: > Got it. I've marked this as a priority lead — our team will reach you within 24 hours to confirm your order for the hoodie in size M for delivery to Dehiwala.
- ✅ Good signals: `marked, priority, team will, reach, within, got it, i've`

**✅ `LC04` — 10.0/10**
- Visitor: "I want to leave"
- Bot: > I understand. Before you go, would you like me to save your current interest via email or WhatsApp so you can easily pick up where you left off later?
- ✅ Good signals: `before you go, pick up where you left off`

### Hot Lead Handling — 10.0/10

**✅ `HL01` — 10.0/10**
- Visitor: "I want to buy this now"
- Bot: > I can certainly help you process that order right away. To lock this in, could you share which item you'd like, your size, your delivery area, and the best phone number to reach you?
- ✅ Good signals: `size, delivery, phone, reach you, lock, could you share, best phone`

**✅ `HL02` — 10.0/10**
- Visitor: "place my order"
- Bot: > I can certainly help you get that processed. To finalize your order, could you please share your preferred size, your delivery area, and the best phone number for our team to reach you?
- ✅ Good signals: `size, delivery, phone`

**✅ `HL03` — 10.0/10**
- Visitor: "I'm ready to buy today"
- Bot: > That's great! To process your order today, please share the specific item you'd like, your size, your delivery area, and the best phone number to reach you.
- ✅ Good signals: `size, delivery, phone, today, process, best phone`

**✅ `HL04` — 10.0/10**
- Visitor: "how do I add this to my cart?"
- Bot: > Perfect! I'll get our team to process your order directly. To lock this in, could you share your preferred item, size, delivery area, and the best phone number to reach you?
- ✅ Good signals: `could you share, delivery, size, phone, i'll get`

### Behavior-Based Triggers — 6.0/10

**🟡 `BT01` — 6.0/10**
- Visitor: "yeah"
- Bot: > Glad to hear it. Since you're looking at the [Hoodie](https://darkgray-goat-264412.hostingersite.com/product/hoodie/), are you shopping for yourself or is this a gift?

**🟡 `BT02` — 6.0/10**
- Visitor: "yes"
- Bot: > Great! Are you looking for our [Hoodie with Pocket](https://darkgray-goat-264412.hostingersite.com/product/hoodie-with-pocket/) or would you prefer to check out our [T-Shirt](https://darkgray-goat-264412.hostingersite.com/product/t-shirt/) selection?

**🟡 `BT03` — 6.0/10**
- Visitor: "yes"
- Bot: > Great! Are you looking to pick up our [Hoodie with Pocket](https://darkgray-goat-264412.hostingersite.com/product/hoodie-with-pocket/) or the [T-Shirt](https://darkgray-goat-264412.hostingersite.com/product/t-shirt/) today?

**🟡 `BT04` — 6.0/10**
- Visitor: "hi"
- Bot: > Hi there! I'm here to help you find what you need. Are you shopping for yourself, a gift, or just exploring today?

### Closing Ability — 9.5/10

**✅ `CL01` — 8.0/10**
- Visitor: "Yeah I think so"
- Bot: > Excellent choice. To get this processed for you, could you share your shipping address and the best phone number to reach you at?
- ✅ Good signals: `ship`

**✅ `CL02` — 10.0/10**
- Visitor: "OK let's do it"
- Bot: > I'm ready to help you get this processed. To lock in your order, could you please share your preferred size, your delivery area, and the best phone number for our team to reach you?
- ✅ Good signals: `size, delivery, phone, process`

**✅ `CL03` — 10.0/10**
- Visitor: "I'll take it"
- Bot: > Great choice! To lock this in, could you share your size, delivery area, and the best phone number to reach you?
- ✅ Good signals: `size, delivery, phone, could you share`

**✅ `CL04` — 10.0/10**
- Visitor: "yes please"
- Bot: > Perfect! I'll get our team to process this for you directly. To lock this in, could you share your size, delivery area, and the best phone number to reach you?
- ✅ Good signals: `size, delivery, phone, process, could you share`
