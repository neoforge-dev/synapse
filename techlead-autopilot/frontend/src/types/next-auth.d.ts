import NextAuth from "next-auth"
import { JWT } from "next-auth/jwt"

declare module "next-auth" {
  interface Session {
    user: {
      id: string
      email: string
      first_name: string
      last_name: string
      job_title: string
      role: string
      organization_id: string
    }
    accessToken: string
    error?: string
  }

  interface User {
    id: string
    email: string
    first_name: string
    last_name: string
    job_title: string
    role: string
    organization_id: string
    access_token: string
    refresh_token: string
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken: string
    refreshToken: string
    accessTokenExpires: number
    user: {
      id: string
      email: string
      first_name: string
      last_name: string
      job_title: string
      role: string
      organization_id: string
    }
    error?: string
  }
}