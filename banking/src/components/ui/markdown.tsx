import React from 'react'
import rehypeRaw from 'rehype-raw'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
// import './markdown.css'

interface MarkdownRendererProps {
    content: string,
    className?: string
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
    return <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
    // components={{
    //     p: (props) => <Text {...props} as='p' />,
    //     ul: (props) => <UnorderedList {...props} />,
    //     ol: (props) => <OrderedList {...props} />,
    //     li: (props) => <ListItem {...props} />,
    //     a: (props) => <Link {...props} />,
    // }}>
    >
        {content}
    </ReactMarkdown>
}

export default MarkdownRenderer