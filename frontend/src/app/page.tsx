import { redirect } from "next/navigation";

export default function Home() {
  // Simple redirect to dashboard - auth hook will handle sending
  // unauthenticated users to login
  redirect("/dashboard");
}
