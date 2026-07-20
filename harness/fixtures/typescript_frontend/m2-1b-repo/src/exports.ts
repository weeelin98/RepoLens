export { value, value as alias, default as primary, type Hidden } from "runtime";
export * from "star-source";
export * as namespace from "namespace-source";
export type { TypeOnly } from "types";

export interface Profile<T> {
  value: T;
}

export type ProfileId = string | number;

export enum Status {
  Ready,
  Done = 2,
}

const enum HiddenStatus {
  Hidden,
}

declare interface AmbientProfile {}
