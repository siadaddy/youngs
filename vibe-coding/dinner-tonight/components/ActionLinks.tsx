import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Linking, useColorScheme } from 'react-native';
import { colors } from '../constants/theme';

interface ActionLink {
  label: string;
  emoji: string;
  appUrl: string;
  webUrl: string;
}

async function openLink(appUrl: string, webUrl: string) {
  try {
    await Linking.openURL(appUrl);
  } catch {
    await Linking.openURL(webUrl);
  }
}

function getLinks(style: string, menu: string): { title: string; links: ActionLink[] } {
  const q = encodeURIComponent(menu);
  const qStore = encodeURIComponent(menu + ' 재료');

  if (style === '집밥') {
    return {
      title: '🛒 재료 바로 구매',
      links: [
        {
          label: '쿠팡',
          emoji: '🚀',
          appUrl: `coupang://search?keyword=${qStore}`,
          webUrl: `https://www.coupang.com/np/search?q=${qStore}`,
        },
        {
          label: '마켓컬리',
          emoji: '🥬',
          appUrl: `kurly://search?sword=${qStore}`,
          webUrl: `https://www.kurly.com/search?sword=${qStore}`,
        },
        {
          label: 'SSG',
          emoji: '🏪',
          appUrl: `ssgpay://`,
          webUrl: `https://www.ssg.com/search.ssg?target=all&query=${qStore}`,
        },
      ],
    };
  }

  if (style === '배달') {
    return {
      title: '🛵 배달 앱으로 주문',
      links: [
        {
          label: '배달의민족',
          emoji: '🍱',
          appUrl: `baemin://search?query=${q}`,
          webUrl: `https://www.baemin.com/`,
        },
        {
          label: '요기요',
          emoji: '🥡',
          appUrl: `yogiyo://search?keyword=${q}`,
          webUrl: `https://www.yogiyo.co.kr/`,
        },
        {
          label: '쿠팡이츠',
          emoji: '⚡',
          appUrl: `coupangeats://search?keyword=${q}`,
          webUrl: `https://www.coupangeats.com/`,
        },
      ],
    };
  }

  if (style === '외식') {
    const qMap = encodeURIComponent(menu + ' 맛집');
    return {
      title: '📍 근처 식당 찾기',
      links: [
        {
          label: '네이버지도',
          emoji: '🗺️',
          appUrl: `nmap://search?query=${qMap}&appname=com.dinnertonight`,
          webUrl: `https://map.naver.com/v5/search/${qMap}`,
        },
        {
          label: '카카오맵',
          emoji: '📍',
          appUrl: `kakaomap://search?q=${qMap}`,
          webUrl: `https://map.kakao.com/?q=${qMap}`,
        },
      ],
    };
  }

  return { title: '', links: [] };
}

interface Props {
  menu: string;
  selectedStyle: string | null;
}

export function ActionLinks({ menu, selectedStyle }: Props) {
  const isDark = useColorScheme() === 'dark';

  if (!selectedStyle || !['집밥', '배달', '외식'].includes(selectedStyle)) return null;

  const { title, links } = getLinks(selectedStyle, menu);

  return (
    <View style={[styles.container, { borderTopColor: isDark ? colors.borderDark : colors.border }]}>
      <Text style={[styles.title, { color: isDark ? '#FFF' : colors.dark }]}>{title}</Text>
      <View style={styles.btnRow}>
        {links.map((link) => (
          <TouchableOpacity
            key={link.label}
            style={[styles.btn, { backgroundColor: isDark ? colors.surfaceDark : colors.surface }]}
            onPress={() => openLink(link.appUrl, link.webUrl)}
            activeOpacity={0.75}
          >
            <Text style={styles.btnEmoji}>{link.emoji}</Text>
            <Text style={[styles.btnLabel, { color: isDark ? '#DDD' : colors.dark }]}>{link.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderTopWidth: 1,
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 8,
  },
  title: {
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 12,
  },
  btnRow: {
    flexDirection: 'row',
    gap: 10,
    flexWrap: 'wrap',
  },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 20,
    gap: 6,
  },
  btnEmoji: { fontSize: 16 },
  btnLabel: { fontSize: 14, fontWeight: '600' },
});
