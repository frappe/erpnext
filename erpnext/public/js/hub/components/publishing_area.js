function get_publishing_header() {
    const title_html = `<h5>${__('Select Products to Publish')}</h5>`;

    const subtitle_html = `<p class="text-muted">
        ${__(`Only products with an image, description and category can be published.
        Please update them if an item in your inventory does not appear.`)}
    </p>`;

    const publish_button_html = `<button class="btn btn-primary btn-sm publish-items" disabled>
        <i class="visible-xs octicon octicon-check"></i>
        <span class="hidden-xs">${__('Publish')}</span>
    </button>`;

    return $(`
        <div class="publish-area empty">
            <div class="publish-area-head">
                ${title_html}
                ${publish_button_html}
            </div>
            <div class="empty-items-container flex align-center flex-column justify-center">
                <p class="text-muted">${__('No Items Selected')}</p>
            </div>
            <div class="row hub-items-container selected-items"></div>
        </div>

        <div class='subpage-title flex'>
            <div>
                ${subtitle_html}
            </div>
        </div>
    `);
}

export {
    get_publishing_header
}
