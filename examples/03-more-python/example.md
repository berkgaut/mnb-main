# GraphViz+Markdown via mnb

In this example `mnb` brings some extra smartness to Markdown+GraphViz combo.

Generator looks through Markdown files and tries to identify images which should be generated from GraphViz .dot files.

For example, if there is a reference to image fig01.png, and there is a file fig01.dot,
then fig01.png would be generated from fig01.dot.

```markdown
![Figure 1](mnb-generated/fig01.png)
```

![Figure 1](mnb-generated/fig01.png)

## Inline GraphViz

If an image reference is immediately followed by code section with language `dot`,
dot code is extracted and transformed into image

![Figure 2](mnb-generated/fig02.png)
```dot mnb.reify=fig02.dot
// comment
digraph Foo {
    node [shape=rectangle, fontsize=12, fontname="Helvetica", label="", color="lightgray", style=filled];

    foo->bar
    bar->bang
    bang->fin
}
```

## External GraphViz as Image Definition

![fig03]

[fig03]: mnb-generated/fig03.png

## Inline GraphViz as Image Definition

If inline GraphViz code follows an image definition, it would be extracted to generate the image

![fig04]

[fig04]: generated/inline-example-2.png
```dot foo=bar baz=bang
digraph Foo {
    node [shape=rectangle, fontsize=12, fontname="Helvetica", label="", color="lightgray", style=filled];

    foo->bar
    bar->bang
    bang->fin
}
```

## Options

"Creative use" of Markdown [link reference definitions](https://spec.commonmark.org/current/#link-reference-definition) to specify options

Subdirectory to store generated images 
```markdown
[mnb-graphviz.option]: generated-dir "mnb-generated"
```
[mnb-graphviz.option]: generated-dir "mnb-generated"


