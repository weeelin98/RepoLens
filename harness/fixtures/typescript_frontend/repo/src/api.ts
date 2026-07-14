export type Profile = { id: string; name: string };

export async function loadProfile(id: string): Promise<Profile> {
  const response = await fetch(`/api/profiles/${id}`);
  return response.json() as Promise<Profile>;
}
