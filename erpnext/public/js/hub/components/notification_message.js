const NotificationMessage = (message) => {
    const $message = $(`<div class="subpage-message">
        <p class="text-muted flex">
            <span>
                ${message}
            </span>
            <i class="octicon octicon-x text-extra-muted"></i>
        </p>
    </div>`);

    $message.find('.octicon-x').on('click', () => {
        $message.remove();
    });

    return $message;
}

export {
    NotificationMessage
}
