import codecs

css_to_append = """
/* Fix for huge speaker icon */
.speaker-btn {
    overflow: hidden;
    padding: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.speaker-icon-img {
    width: 22px !important;
    height: 22px !important;
    min-width: 22px;
    min-height: 22px;
    object-fit: contain;
    display: block;
}

.speaker-btn.mini .speaker-icon-img {
    width: 14px !important;
    height: 14px !important;
    min-width: 14px;
    min-height: 14px;
}

.option-speaker .speaker-icon-img {
    width: 18px !important;
    height: 18px !important;
}
"""

with codecs.open('style.css', 'a', encoding='utf-16') as f:
    f.write(css_to_append)

print("Fixed speaker icon sizes successfully!")
