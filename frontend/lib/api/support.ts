import { apiRequest } from "./client";

export type FAQItem = {
  q: string;
  a: string;
};

export const supportApi = {
  getFAQ: () =>
    apiRequest<{ items: FAQItem[] }>("/support/faq"),

  submitContact: (body: { email: string; subject: string; message: string }) =>
    apiRequest<{ ticket_id: string }>("/support/contact", {
      method: "POST",
      body,
    }),
};
