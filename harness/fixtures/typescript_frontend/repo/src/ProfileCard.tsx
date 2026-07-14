import { useEffect, useState } from "react";
import { loadProfile, type Profile } from "./api";

export function ProfileCard({ id }: { id: string }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  useEffect(() => { void loadProfile(id).then(setProfile); }, [id]);
  return <h2>{profile?.name ?? "Loading"}</h2>;
}
