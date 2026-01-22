"""Post submitter - handles submitting posts to Reddit."""

from typing import Optional


class PostSubmitter:
    """Handles submitting posts and crossposts to Reddit."""

    def __init__(self, reddit, config):
        """Initialize with PRAW instance and config.
        
        Args:
            reddit: PRAW Reddit instance
            config: BotConfig instance
        """
        self.reddit = reddit
        self.config = config

    def submit_link(
        self, 
        title: str, 
        url: str, 
        flair_id: Optional[str] = None, 
        body: str = ""
    ) -> Optional[str]:
        """Submit a link post to target subreddit.
        
        Args:
            title: Post title
            url: URL to link to
            flair_id: Optional flair ID to assign
            body: Optional body text to add after submission
            
        Returns:
            Reddit ID of submitted post, or None if failed
        """
        try:
            subreddit = self.reddit.subreddit(self.config.target_sub)
            submission = subreddit.submit(title=title, url=url, flair_id=flair_id)
            
            # Add body text if provided
            if body:
                submission.edit(body)
                
            return submission.id
        except Exception as e:
            print(f"❌ Failed to submit link: {e}")
            return None

    def crosspost(
        self, 
        post, 
        title: str, 
        flair_id: Optional[str] = None
    ) -> Optional[str]:
        """Create a crosspost in target subreddit.
        
        Args:
            post: Original PRAW submission to crosspost
            title: Title for the crosspost
            flair_id: Optional flair ID to assign
            
        Returns:
            Reddit ID of crosspost, or None if failed
        """
        try:
            subreddit = self.reddit.subreddit(self.config.target_sub)
            
            # If this is itself a crosspost, get the original
            post_to_cross = post
            if hasattr(post, "crosspost_parent_list") and post.crosspost_parent_list:
                orig_id = post.crosspost_parent_list[0]["id"]
                post_to_cross = self.reddit.submission(id=orig_id)
            
            # Create the crosspost
            submission = post_to_cross.crosspost(
                subreddit=self.config.target_sub, 
                send_replies=False, 
                title=title, 
                flair_id=flair_id
            )
            
            return submission.id
        except Exception as e:
            print(f"❌ Failed to create crosspost: {e}")
            return None
