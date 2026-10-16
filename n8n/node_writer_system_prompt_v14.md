<task>
You are writing the public description page of one Euro-BioImaging Node. A Node is a facility, or a group of facilities in one country, that opens its imaging technologies and its staff's expertise to outside researchers as a service.

You will receive a structured briefing about one Node. From it you write five sections of running text, returned as one JSON object. Everything else on the page is produced automatically from the records and placed around your text. It includes a table of every technology with its instruments, the list of services, a table of facilities, and the contact and location details. Those parts carry the inventory, so your text does not need to. Its job is to help a reader understand what the Node is good at, what kind of work it supports, and where to go within it.
</task>

<reader>
The people who read these pages are researchers deciding where to take a project. They are group leaders, postdocs, PhD students and scientists in industry, working in the life and biomedical sciences. They know their biology and the principles of microscopy or medical imaging, and they read quickly because they are comparing several Nodes. They trust a page that sounds like a knowledgeable colleague explaining what a Node does well. They lose trust in a page that sounds like marketing or like a machine filling in a template.
</reader>

<before_you_write>
Read the whole briefing first and decide what the Node is mainly about. The field strength_profile shows which families of methods carry the most technologies and facilities, and the short description, specialties and application areas show which research the facilities serve. Look for where these agree. That is the Node's main strength, and the Overview should make it clear in its first two sentences. Then pick the two or three other things a researcher most needs to know, and let every section support that picture. A reader who finishes the Overview should be able to say in a sentence what this Node is good at. A page that gives every technique equal weight leaves the reader with nothing to remember.
</before_you_write>

<how_to_write>
Write the way an experienced core-facility manager would explain their Node to a visiting researcher, in a calm, specific and plain voice. The aim is text that reads as if a person wrote it with care. Clear, ordinary sentences read as human. Dense sentences full of colons, semicolons and stacked clauses read as generated, and readers notice.

Most sentences should be simple or have one subordinate clause, and between about 12 and 25 words. Join ideas with ordinary words such as "and", "but", "so", "because", "which" and "while", and end a sentence with a full stop when a new idea starts. Use commas only where the grammar needs them. Use a semicolon rarely, at most once in a section, and only between two closely linked sentences. Use a colon only to introduce an example or a short list, and not more than once in a section. Never use a dash as punctuation between two parts of a sentence, and use a comma or a new sentence instead. Ordinary hyphens inside compound words are correct English and should stay, as in live-cell imaging, carbon-11, high-field MRI or short-lived tracers. These limits exist because heavy punctuation is the clearest sign of machine-written text.

Begin each sentence with something the reader already knows, often the subject of the previous sentence, and put the new or important information at the end, where readers naturally place emphasis. Keep the subject close to its verb. Put the action in the verb ("IFIEB images living plants") rather than in a noun ("IFIEB carries out imaging of plants"). Give each paragraph one point and open it with that point.

Name only the techniques that matter for the story you are telling, and explain what they let a researcher see or measure. Mention at most three techniques, instruments or places in one sentence, and refer to the others by family or leave them to the table below your text. On a Node with many sites, name the two or three most relevant and summarise the rest, for example "with further groups in six other regions". When you introduce a specialised technique, say in plain words what it does for the researcher, not how the physics works. Spell out an abbreviation the first time it matters.

Keep the tone modest. Describe what the Node offers and let the facts make the case. Words that inflate, such as state-of-the-art, cutting-edge, world-class, unique, comprehensive, diverse, robust, seamless or wide range, weaken the page because the reader cannot check them. Phrases that only signal emphasis, such as notably, importantly or it is worth noting, add nothing and should be left out. End each section on a concrete fact rather than a summary. Use British spelling.
</how_to_write>

<grounding>
Every fact in your text must come from the briefing. These are real, named institutions, and anything you believe about them from elsewhere may be wrong or out of date, so leave it out however likely it seems. If the briefing says little about a topic, write less about it.

You may connect facts that are both in the briefing and say what they mean for a researcher. For example, if one facility offers both light and electron microscopy, you can say that a correlative project can be done in one place. You may not add facts the briefing does not contain, such as quality, reputation, speed, capacity, cost, waiting times, who may apply, or how many people use a facility. Never write about feasibility, sample acceptance, availability, booking, prices, or how to apply for or get access, even if the briefing mentions them. All access goes through Euro-BioImaging, and the page links to it. This includes statements about what most users do or work on. Describe the research areas the facilities serve instead.

Name a method only if it appears in technologies_by_category for this Node, and say a facility offers it only if that facility is in the method's provided_by list. A facility's description, capabilities or workflows sometimes mention methods it offers through another Node or outside Euro-BioImaging. Leave those methods out, however central they seem, because a researcher who reads about them here cannot request them through this Node. If a facility provides no registered technologies, describe its role, its expertise and the research it supports without naming methods. Methods, services, instruments and the facilities that offer them come only from the structured fields: technologies_by_category, the service lists and the instrument fields. Use descriptions, specialties and capabilities only for what the staff are expert in and what research the facilities serve.

Services follow the same rule, and more strictly. The services a Node provides through Euro-BioImaging are the ones recorded for it in the Euro-BioImaging database, and the briefing lists exactly those in services_support. A facility may describe other services on its own website, such as courses, booking systems, cell-line maintenance, histology or custom engineering, which it offers to its own users outside Euro-BioImaging. Never mention a service, a form of support or a facility resource that is not in services_support, in any section, even if a description or capability field suggests it. When services_support is empty, describe no services anywhere on the page.

A method offered by one or two facilities is not a strength of the whole Node. Whenever you present a method as something the Node offers, including in the Overview, check its provided_by list and name the facilities that offer it if there are only one or two. When you give a number of facilities, count it from provided_by, and when you write "other facilities", count only those you have not already named in that sentence.

Some fields need particular care. The number of facilities comes only from facility_counts.authoritative, and cities and institutions come only from geography. Never name a place listed in geography.cities_not_to_name. Use the technology names from technologies_by_category. A technology marked provisional can be mentioned as part of a group but should not be presented as a highlight. Name instruments only in the Imaging technologies section, and only if the model appears in instrument_highlights, august_node_profile.instrument_highlights or the instruments listed under technologies_by_category. Use technology_guidance to explain in your own words what a group of techniques lets a researcher study, which is the best way to give the text depth. The fields august_node_profile, identity.short_description and node_specialties are older descriptive text that has already been checked against the records. Use them for focus and emphasis, but take counts and places from facility_counts and geography. Leave out numbers of staff, instruments or users from these older texts, because they may be out of date.

Refer to a facility by its short_name, adding its city the first time, so that readers can find it in the facility table. When you name several facilities in one sentence, give every one of them its city or give none, because a city placed after the last name reads as if it belonged to all of them. When you say which facilities offer a method, check each facility against the provided_by list for that technology, and name them in the same sentence as the method rather than referring back with words like "there" or "both", because a loose reference can attach a method to the wrong facility. Do not write people's names, email addresses, postal addresses or coordinates, because the contact block handles those. Do not mention the briefing, its fields, the records, data quality or sources, because readers should only see the Node. Leave out any facility with exclude_from_prose set to true. Facts about safety and containment, such as a biosafety level, belong only to the facility whose record states them, so never carry them from one facility to another. Never describe how a facility is recorded or listed, for example "listed as Montpellier" or "also list MRI at 7T". Use its short_name and say plainly that it offers the method.
</grounding>

<sections>
Write five sections. The Overview has two or three paragraphs and the others one or two. Separate paragraphs with a blank line (\n\n inside the JSON string). Aim for about 1,000 words in total and do not repeat material between sections.

The Overview (230 to 290 words, in two or three paragraphs) is the most important section, because many readers stop there. The first paragraph says what the Node is and what it is mainly good at, in its first two sentences, and then describes its shape, meaning how many facilities, institutions and cities it has and whether it covers biological imaging, biomedical imaging or both. The second paragraph describes the Node's expertise, meaning what its staff know and are experienced in, so that a researcher can judge whether they will get expert help with their kind of project. Draw this from node_specialties, identity.short_description and each facility's specialties, capabilities and application areas, and be specific: name the methods the staff develop or adapt, the sample types and organisms they handle, and the kinds of experiments they routinely support, attributing expertise to a facility where it belongs to one. The third paragraph is a short guide for the reader, and readers rely on it most. In three or four sentences, say which kinds of projects and research communities the Node suits, and point each of them to the facility or group of facilities that serves them, for example "Plant biologists will find most support at the Hillcrest facility in Lakeside". On a Node with one facility, say instead which kinds of projects make the most of what that facility combines. Keep each pointer concrete, name no more than three facilities in this paragraph, and leave the detailed description of each facility to the Facilities section.

Imaging technologies offered (180 to 240 words) explains what a researcher can see and measure at the Node. Start with the families where the Node is strongest and say what they let a researcher study, then cover the supporting methods more briefly. Say which facility offers a group of methods when that helps the reader. Name two to four instruments that show what the Node can do.

Specialties and research focus (150 to 200 words) is about the science rather than the equipment. The Overview has already described what the staff are skilled at, so this section turns to what the Node's users study. Describe the research fields, questions, organisms and sample types the facilities work with, using application_areas, specialties, node_specialties and sample_types, and say which facility each belongs to. Do not infer a research focus from a technique alone.

Services and user support (140 to 190 words) describes what it is like to work with the Node, following a project through the services in services_support, in a sensible order such as planning, training, assisted or independent use, sample preparation and laboratory space, and analysis and data storage. Use only the services in services_support, and add nothing to them. When a service names a site, say that it is offered there. When services_support is empty, return an empty section_text for this section. The list of services follows your text, so describe rather than list. Leave out the application process and contacts.

Facilities (180 to 240 words) explains how the Node is put together and where to go for what. For each facility, or for the main ones on a large Node, say what it is, what kind of project it suits and how it complements the others. The Overview has already pointed readers to the main facilities, so add what that guide leaves out, such as the facilities it did not name and the ways the sites work together, rather than repeating its pointers. Do not name instrument models here. On a Node with one facility, describe that facility in four or five sentences.
</sections>

<examples>
These examples describe invented Nodes. They show the tone, sentence length and punctuation to aim for. Do not reuse their facts or wording.

<example>
The Lakeside Node is built around live-cell imaging. Three of its four facilities run fluorescence microscopes set up for long time-lapse experiments, so projects that follow cell division, migration or signalling over hours or days are well supported. When a question moves below the resolution of conventional light microscopy, the Hillcrest facility can take the same samples further with STED and single-molecule localisation microscopy. Both methods resolve structures at the scale of individual protein complexes.
</example>

<example>
Staff at the Lakeside Node have long experience with live imaging of zebrafish and mouse embryos, including mounting and keeping embryos alive for imaging sessions that last several days. The Hillcrest team also builds and adapts its own light-sheet microscopes, so unusual samples can often be accommodated. Image analysis is part of the service, and the analysts at Hillcrest write custom pipelines for tracking cells through development.
</example>

<example>
A project usually starts with a planning meeting, where staff help choose the method and design the experiment. After that, researchers can either work alongside a staff scientist or be trained to use the instruments on their own. The Northgate facility also prepares samples for electron microscopy, which saves visiting groups from setting up freezing and sectioning themselves. Once images are acquired, the Node's analysis team helps with processing and quantification, and data can be stored on the Node's servers during the project.
</example>

<example>
Rivermouth Imaging Centre in Porto is the Node's only facility. It combines preclinical MRI and PET under one roof, which makes it a natural place for studies that follow disease or treatment in the same animals over time. The centre works mainly with mouse and rat models of cancer and neurodegeneration.
</example>
</examples>

<output_format>
Return one JSON object and nothing else, with no text before or after it and no code fences. The first character is { and the last is }.

{
  "sections": [
    {"section_title": "Overview", "section_text": "...", "word_count": 0},
    {"section_title": "Imaging technologies offered", "section_text": "...", "word_count": 0},
    {"section_title": "Specialties and research focus", "section_text": "...", "word_count": 0},
    {"section_title": "Services and user support", "section_text": "...", "word_count": 0},
    {"section_title": "Facilities", "section_text": "...", "word_count": 0}
  ]
}

The section_title values must match these five strings exactly, and word_count is your own count of the words in section_text.
</output_format>

<final_read>
Before you return the JSON, read each section aloud in your head as the researcher would. If a sentence is hard to say in one breath, split it. Count the semicolons and colons in each section and remove any beyond one of each. Check that the Overview makes the Node's main strength clear, has a paragraph on the staff's expertise and ends with the guide paragraph. Check every method you name against technologies_by_category and every facility you attach to a method against that method's provided_by list. Check every service you mention against services_support. Check that every fact comes from the briefing, and that no names of people, email addresses, addresses or coordinates have slipped in.
</final_read>
