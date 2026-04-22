# Web Design & CSS Styling Skill

## Purpose
This skill provides guidelines and best practices for creating HTML pages with CSS styling.

## When to Use
- Creating HTML pages
- Styling web content with CSS
- Designing user interfaces
- Making responsive layouts

## CSS Best Practices

### 1. Structure
```css
/* Use clear, semantic selectors */
body {
    font-family: 'Arial', sans-serif;
    margin: 0;
    padding: 0;
    line-height: 1.6;
}

/* Group related styles */
h1, h2, h3 {
    color: #333;
    margin-bottom: 1rem;
}
```

### 2. Color Schemes
- Use consistent color palette (3-5 colors max)
- Ensure good contrast for readability
- Consider accessibility (WCAG guidelines)

### 3. Layout
```css
/* Modern flexbox/grid layouts */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.flex-container {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
}
```

### 4. Responsive Design
```css
/* Mobile-first approach */
.element {
    width: 100%;
}

@media (min-width: 768px) {
    .element {
        width: 50%;
    }
}

@media (min-width: 1024px) {
    .element {
        width: 33.333%;
    }
}
```

### 5. Typography
```css
/* Clear hierarchy */
h1 { font-size: 2.5rem; }
h2 { font-size: 2rem; }
h3 { font-size: 1.5rem; }
p { font-size: 1rem; }

/* Readable line length */
p {
    max-width: 65ch;
    line-height: 1.6;
}
```

## HTML Structure Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page Title</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <nav>
            <!-- Navigation -->
        </nav>
    </header>
    
    <main>
        <section>
            <!-- Main content -->
        </section>
    </main>
    
    <footer>
        <!-- Footer content -->
    </footer>
</body>
</html>
```

## Themed Design Examples

### Cat Theme
```css
:root {
    --primary-color: #ff6b6b;
    --secondary-color: #4ecdc4;
    --accent-color: #ffe66d;
    --text-color: #2d3436;
    --bg-color: #f8f9fa;
}

body {
    background-color: var(--bg-color);
    color: var(--text-color);
}

.cat-card {
    background: white;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    transition: transform 0.3s ease;
}

.cat-card:hover {
    transform: translateY(-5px);
}

.paw-print {
    color: var(--primary-color);
    font-size: 2rem;
}
```

## Workflow

1. **Plan the structure**: Sketch layout, identify sections
2. **Write semantic HTML**: Use proper tags (header, nav, main, section, article, footer)
3. **Create CSS file**: Start with reset/normalize, then layout, then components
4. **Link CSS to HTML**: `<link rel="stylesheet" href="style.css">`
5. **Test responsiveness**: Check on different screen sizes
6. **Validate**: Use W3C validators for HTML and CSS

## Common Patterns

### Card Layout
```css
.card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

### Button Styles
```css
.button {
    display: inline-block;
    padding: 10px 20px;
    background-color: #007bff;
    color: white;
    text-decoration: none;
    border-radius: 5px;
    transition: background-color 0.3s ease;
}

.button:hover {
    background-color: #0056b3;
}
```

### Image Handling
```css
img {
    max-width: 100%;
    height: auto;
    display: block;
}

.img-rounded {
    border-radius: 50%;
}
```

## Tips
- Keep CSS organized (use comments to separate sections)
- Use CSS variables for colors and repeated values
- Minimize use of `!important`
- Test in multiple browsers
- Optimize images before using
- Use meaningful class names (BEM methodology recommended)

## Resources
- MDN Web Docs: https://developer.mozilla.org/en-US/docs/Web/CSS
- CSS-Tricks: https://css-tricks.com/
- Can I Use: https://caniuse.com/ (browser compatibility)
