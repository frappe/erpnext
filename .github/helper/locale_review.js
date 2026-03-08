module.exports = async ({ github, context, localeChanged }) => {
  const pr = context.payload.pull_request.number
  const { owner, repo } = context.repo
  
  const { data: me } = await github.rest.users.getAuthenticated()
  const botUser = me.login

  const reviews = await github.rest.pulls.listReviews({
    owner,
    repo,
    pull_number: pr
  })

  const botReview = reviews.data
    .reverse()
    .find(r => r.user.login === botUser && r.state === "CHANGES_REQUESTED")

  if (localeChanged) {
    if (!botReview) {
      await github.rest.pulls.createReview({
        owner,
        repo,
        pull_number: pr,
        event: "REQUEST_CHANGES",
        body: "Translations are managed through [Crowdin](https://crowdin.com/project/frappe/). Consider contributing through Crowdin."
      })
    }
  } else {
    if (botReview) {
      await github.rest.pulls.dismissReview({
        owner,
        repo,
        pull_number: pr,
        review_id: botReview.id,
        message: ""
      })
    }
  }
}