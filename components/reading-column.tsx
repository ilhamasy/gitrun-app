"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeCell } from "@/components/code-cell";
import { extractHeadings, numberHeadings, slugifyHeading } from "@/lib/stations";

interface ReadingColumnProps {
  content: string;
}

function textOf(children: React.ReactNode): string {
  return React.Children.toArray(children)
    .map((child) => {
      if (typeof child === "string") return child;
      if (React.isValidElement<{ children?: React.ReactNode }>(child)) {
        return textOf(child.props.children);
      }
      return "";
    })
    .join("");
}

export function ReadingColumn({ content }: ReadingColumnProps) {
  // Section numbers come from the same heading parse the page index uses, so
  // the margin address and the citation address can never disagree.
  const codes = new Map(
    numberHeadings(extractHeadings(content)).map((heading) => [
      heading.id,
      heading.code,
    ])
  );

  return (
    <div className="reading">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="signage !mt-0 mb-5 text-[2.5rem] sm:text-[2.75rem]">
              {children}
            </h1>
          ),
          h2: ({ children }) => {
            const id = slugifyHeading(textOf(children));
            const code = codes.get(id);
            return (
              <h2 id={id}>
                <span>
                  {children}
                  <a
                    href={`#${id}`}
                    className="anchor-link ml-2"
                    aria-label={`Link to section ${code ?? id}`}
                  >
                    #
                  </a>
                </span>
                {code && (
                  <a
                    href={`#${id}`}
                    className="station-index"
                    aria-label={`Section ${code}`}
                  >
                    §{code}
                  </a>
                )}
              </h2>
            );
          },
          h3: ({ children }) => {
            const id = slugifyHeading(textOf(children));
            const code = codes.get(id);
            return (
              <h3 id={id}>
                {children}
                <a
                  href={`#${id}`}
                  className="anchor-link ml-2"
                  aria-label={`Link to section ${code ?? id}`}
                >
                  #
                </a>
              </h3>
            );
          },
          h4: ({ children }) => {
            const id = slugifyHeading(textOf(children));
            return <h4 id={id}>{children}</h4>;
          },
          code: ({ className, children, ...props }) => {
            const isInline =
              !className && typeof children === "string" && !children.includes("\n");
            if (isInline) {
              return <code {...props}>{children}</code>;
            }
            return <CodeCell className={className}>{children}</CodeCell>;
          },
          pre: ({ children }) => <>{children}</>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
