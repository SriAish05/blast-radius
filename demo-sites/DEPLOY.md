# Put the demo sites online (Netlify, free, about 10 minutes)

Each folder below becomes one website. Use these exact Netlify names so the links match the answer key:

| Folder | Netlify site name | Link |
|---|---|---|
| cdn | cdn-demo | https://cdn-demo.netlify.app |
| bakery | bakery-demo | https://bakery-demo.netlify.app |
| clinic | clinic-demo | https://clinic-demo.netlify.app |
| coaching | coaching-demo | https://coaching-demo.netlify.app |

Do NOT deploy `cdn-hacked` as its own site. It is only used during the demo (see below).

## For each folder
1. Go to https://app.netlify.com/drop and log in (free account).
2. Drag the folder (e.g. `cdn`) onto the page. It uploads and gives a random name.
3. Site configuration > Change site name > type the name from the table > Save.
4. Open the link and check the page loads.

If a name is taken, pick another (e.g. `br26-cdn`), then run:
`python demo-sites/set_names.py cdn-demo=br26-cdn` and re-upload the changed site folders.

## Check
- https://bakery-demo.netlify.app shows a "Chat with us" bubble (this proves the runtime chain works).
- https://bakery-demo.netlify.app/contact opens.

## The live "hack" in the demo
1. Open the cdn-demo site in Netlify > Deploys.
2. Drag the `cdn-hacked` folder onto the Deploys page. The bakery page now shows a red DEMO COMPROMISE banner.
3. To undo: drag the `cdn` folder onto the Deploys page again.
