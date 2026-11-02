import type { TextKey } from '../../text/en'

// The people behind WeatherWise. A photo is optional: without one the card shows initials.
export interface Member {
  name: string
  initials: string
  photo?: string
  role: TextKey
  bio: TextKey
  links: { label: string; href: string }[]
}

export const TEAM: Member[] = [
  {
    name: 'Prashant Mahajan',
    initials: 'PM',
    role: 'site.prashantRole',
    bio: 'site.prashantBio',
    links: [
      { label: 'LinkedIn', href: 'https://www.linkedin.com/in/prashantmahajan92/' },
      { label: 'pmahajan.dev', href: 'https://www.pmahajan.dev/' },
      { label: 'GitHub', href: 'https://github.com/pm19nov' },
    ],
  },
  {
    name: 'Prince Birring',
    initials: 'PB',
    photo: '/team/prince-birring.jpg',
    role: 'site.princeRole',
    bio: 'site.princeBio',
    links: [
      { label: 'LinkedIn', href: 'https://www.linkedin.com/in/prince-birring-devops-engineer/' },
      { label: 'GitHub', href: 'https://github.com/princebirring' },
    ],
  },
]

export const REPO = 'https://github.com/princebirring/weatherwise'
